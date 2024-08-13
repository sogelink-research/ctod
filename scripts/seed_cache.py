import argparse
import asyncio
import os
import aiohttp
import sys
import time
import math
import logging
import gzip

from concurrent.futures import Future
from ctod.core import utils
from ctod.core.layer import generate_layer_json
from ctod.core.tile_cache import get_tile_from_disk, save_tile_to_disk, get_root_folder
from morecantile import TileMatrixSet
from uvicorn import Config, Server

from ctod.server.queries import QueryParameters
import json


def setup_logging(log_level=logging.INFO):
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_layer_json(tms: TileMatrixSet, filepath: str, max_zoom: int = 22) -> dict:
    qp = QueryParameters(cog=filepath, maxZoom=max_zoom)
    json_string = generate_layer_json(tms, qp)
    return json_string


def create_cache_folder(filepath: str):
    if not os.path.exists(filepath):
        try:
            os.makedirs(filepath)
        except Exception as e:
            logging.error(f"Failed to create cache folder: {e}")
            sys.exit(1)


def get_tile_range(layer_json: dict, zoom: int):
    available = layer_json["available"]
    info = available[zoom][0]
    return (info["startX"], info["endX"], info["startY"], info["endY"])


async def seed_cache(
    server: Server,
    tms: TileMatrixSet,
    input_filepath: str,
    output_filepath: str,
    meshing_method: str,
    params: str,
    zoom_levels: list,
    overwrite: bool,
    done_future: Future,
    port: int,
    request_count: int,
    layer_json_max_zoom: int,
    no_gzip: bool
):
    create_cache_folder(output_filepath)
    logging.info(f"Starting to get layer.json")
    layer_json = get_layer_json(tms, input_filepath)

    if layer_json_max_zoom:
        save_layer_json(output_filepath, input_filepath,
                        meshing_method, layer_json_max_zoom, layer_json)

    logging.info(f"Finished getting layer.json")

    for zoom in zoom_levels:
        if server.should_exit:  # Check if the server has been stopped
            break
        await generate_level(
            server,
            tms,
            input_filepath,
            output_filepath,
            layer_json,
            zoom,
            meshing_method,
            params,
            overwrite,
            port,
            request_count,
            no_gzip,
        )

    logging.info(f"Finished seeding cache, stopping...")
    done_future.set_result(None)


def save_layer_json(output_filepath: str, file, meshing_method, layer_json_max_zoom, layer_json: dict):
    """Write a layer.json file that can be used to host the cache using a web server."""

    json_copy = layer_json.copy()
    json_copy["tiles"] = ["{z}/{x}/{y}.terrain"]
    root_folder = get_root_folder(output_filepath, file, meshing_method)
    json_copy["available"] = json_copy["available"][:layer_json_max_zoom + 1]

    try:
        with open(os.path.join(root_folder, "layer.json"), "w") as f:
            json.dump(json_copy, f)
    except Exception as e:
        logging.error(f"An error occurred saving layer.json: {e}")
    finally:
        logging.debug("Exiting save_layer_json")


def interleave_bits(x, y):
    """Interleave the bits of x and y. This is a key part of generating the Z-order curve."""
    z = 0
    for i in range(32):
        z |= (x & 1 << i) << i | (y & 1 << i) << (i + 1)
    return z


def generate_z_order_grid(x_range, y_range):
    """Generate a grid of points in the x-y plane, sorted by Z-order."""

    grid = [(x, y) for x in x_range for y in y_range]
    grid.sort(key=lambda point: interleave_bits(point[0], point[1]))
    return grid


async def generate_level(
    server: Server,
    tms: TileMatrixSet,
    input_filepath: str,
    output_filepath: str,
    layer_json: dict,
    zoom: int,
    meshing_method: str,
    params: str,
    overwrite: bool,
    port: int,
    request_count: int,
    no_gzip: bool
):
    tile_range = get_tile_range(layer_json, zoom)
    x_range = range(tile_range[0], tile_range[1] + 1)
    y_range = range(tile_range[2], tile_range[3] + 1)
    morton_order = generate_z_order_grid(x_range, y_range)

    logging.info(
        f"""Generating cache for zoom level {zoom} with {
            len(x_range) * len(y_range)} tile(s)"""
    )

    start_time = time.time()
    generated_tiles = 0

    tasks = []

    for x, y in morton_order:
        if server.should_exit:  # Check if the server has been stopped
            break

        task = asyncio.create_task(
            generate_tile(
                input_filepath,
                output_filepath,
                tms,
                x,
                y,
                zoom,
                meshing_method,
                params,
                overwrite,
                port,
                no_gzip,
            )
        )
        tasks.append(task)

        if len(tasks) >= request_count:
            await asyncio.gather(*tasks)
            tasks = []

        generated_tiles += 1
        if generated_tiles % 100 == 0:
            elapsed_time = time.time() - start_time
            estimated_time = (elapsed_time / generated_tiles) * (
                len(x_range) * len(y_range) - generated_tiles
            )
            estimated_time_minutes = math.floor(estimated_time / 60)
            estimated_time_seconds = math.ceil(estimated_time % 60)
            logging.info(
                f"""Done {generated_tiles}/{len(x_range) * len(y_range)} for zoom {zoom}. Estimated time remaining: {
                    estimated_time_minutes:02d}:{estimated_time_seconds:02d}"""
            )

        if generated_tiles == len(x_range) * len(y_range):
            elapsed_time = time.time() - start_time
            elapsed_time_minutes = math.floor(elapsed_time / 60)
            elapsed_time_seconds = math.ceil(elapsed_time % 60)
            logging.info(
                f"""Generation completed for zoom level {zoom}. Total elapsed time: {
                    elapsed_time_minutes:02d}:{elapsed_time_seconds:02d}"""
            )

    if tasks:
        await asyncio.gather(*tasks)

    logging.info(f"Finished generating cache for zoom level {zoom}")


async def generate_tile(
    input_filepath: str,
    output_filepath: str,
    tms,
    x: int,
    y: int,
    z: int,
    meshing_method: str,
    params: str,
    overwrite: bool,
    port: int,
    no_gzip: bool
):

    # If overwrite is false, skip generating and caching the tile
    if not overwrite:
        cached_tile = await get_tile_from_disk(
            output_filepath, input_filepath, tms, meshing_method, z, x, y
        )
        if cached_tile is not None:
            return

    tile_url = f"""http://localhost:{port}/tiles/dynamic/{z}/{x}/{y}.terrain?cog={
        input_filepath}&skipCache=true&meshingMethod={meshing_method}"""
    if params is not None:
        tile_url += f"&{params}"

    headers = {
        "Accept": "application/vnd.quantized-mesh;extensions=octvertexnormals",
        "Accept-Encoding": "gzip",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(tile_url, headers=headers) as response:
            try:
                if response.status == 200:
                    tile_data = await response.read()
                    ix, iy, iz = utils.invert_y(tms, x, y, z)

                    if not no_gzip:
                        tile_data = gzip.compress(tile_data)

                    await save_tile_to_disk(
                        output_filepath,
                        input_filepath,
                        tms,
                        meshing_method,
                        iz,
                        ix,
                        iy,
                        tile_data,
                    )
                else:
                    logging.error(
                        f"""Failed to generate tile {x} {y} {
                            z}. Status code: {response.status}"""
                    )
            except Exception as e:
                logging.error(f"""Failed to generate tile {
                              x} {y} {z}. Error: {e}""")


async def clear_tasks():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)


async def run(parser: argparse.ArgumentParser):
    try:
        args = parser.parse_args()
        port = int(args.port)
        request_count = int(args.request_count)
        zoom_levels = list(map(int, args.zoom_levels.split("-")))
        layer_json_max_zoom = int(
            args.export_layer_json) if args.export_layer_json else None
        no_gzip = args.no_gzip

        # Clear all arguments
        sys.argv = []

        os.environ["CTOD_PORT"] = str(port)
        os.environ["CTOD_UNSAFE"] = "false"
        os.environ["CTOD_LOGGING_LEVEL"] = "info"
        os.environ["WORKERS_PER_CORE"] = "1"
        os.environ["CTOD_DB_NAME"] = "seed_cache.db"

        tms = utils.get_tms()
        config = Config(
            "ctod.server.fastapi:app",
            host="0.0.0.0",
            port=port,
            log_config=None,
            reload=False,
            workers=1,
        )
        server = Server(config)

        loop = asyncio.get_event_loop()
        server_task = loop.create_task(server.serve())
        await asyncio.sleep(2)

        done_future = Future()

        seed_cache_task = asyncio.create_task(
            seed_cache(
                server,
                tms,
                args.input,
                args.output,
                args.meshing_method,
                args.params,
                zoom_levels,
                args.overwrite,
                done_future,
                port,
                request_count,
                layer_json_max_zoom,
                no_gzip
            )
        )

        # Wait for the done_future to be set
        while not done_future.done():
            # Sleep for a short period to prevent busy waiting
            await asyncio.sleep(0.1)

        # Once the done_future is set, stop the server
        server.should_exit = True
        await server_task  # Wait for the server task to finish

        await clear_tasks()

    except KeyboardInterrupt:
        # On KeyboardInterrupt, stop the server and cancel all running tasks
        server.should_exit = True
        await clear_tasks()

    finally:
        if loop:
            loop.stop()


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Seed the cache")
    parser.add_argument(
        "-i",
        "--input",
        metavar="input_dataset",
        required=True,
        help="input dataset, can be a cog, vrt or mosaic, make sure the path/url is exactly the same as the one being supplied to the server when requesting tiles.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="output_folder",
        default="./cache",
        help="Specify the output folder for the cache.",
    )
    parser.add_argument(
        "-m",
        "--meshing-method",
        metavar="meshing_method",
        default="grid",
        help="The meshing method to use: grid, delatin, martini. Defaults to grid.",
    )
    parser.add_argument(
        "-z",
        "--zoom-levels",
        metavar="zoom_levels",
        required=True,
        help="The zoom levels to create a cache for. Separate multiple levels with '-'.",
    )
    parser.add_argument(
        "--port",
        metavar="port",
        required=False,
        default="5580",
        help="The port to run the server on. Defaults to 5580.",
    )
    parser.add_argument(
        "-r",
        "--request-count",
        metavar="request_count",
        required=False,
        default="10",
        help="Amount of simultaneous requests send to CTOD. Defaults to 10.",
    )
    parser.add_argument(
        "-p",
        "--params",
        metavar="request_parameters",
        required=False,
        default=None,
        help="Pass options to tile requests, e.g. 'resamplingMethod=bilinear&defaultGridSize=20'. Defaults to None.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Add --overwrite to overwrite existing tiles in the cache. Defaults to False.",
    )
    parser.add_argument(
        "--export-layer-json",
        metavar="export_layer_json",
        required=False,
        default=None,
        help="Add --export-layer-json followed by the max zoom level to create a layer.json in the root directory.",
    )

    parser.add_argument(
        "--no-gzip",
        action="store_true",
        help="Add --no-gzip to disable gzip compression. Defaults to False. Only use if you are gong to statically serve the tiles and don't want to use gzip compression.",
    )

    asyncio.run(run(parser))


if __name__ == "__main__":
    main()
