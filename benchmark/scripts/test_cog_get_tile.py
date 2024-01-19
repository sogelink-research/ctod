import argparse
import json
import timeit
import time

from concurrent.futures import ThreadPoolExecutor
from morecantile import TileMatrixSet, tms
from rio_tiler.io import Reader

def download(cog: str, tms: TileMatrixSet, tile_info: dict, resampling_method: str = "bilinear") -> float:
    def _download():
        with Reader(cog, tms=tms) as src:
            image_data = src.tile(tile_z=tile_info['z'], tile_x=tile_info['x'], tile_y=tile_info['y'], resampling_method=resampling_method)

    return timeit.timeit(_download, number=1) * 1000

def process_tile(cog: str, tms: TileMatrixSet, tile_info: dict, count: int, parallel: bool):
    if parallel:
        with ThreadPoolExecutor() as executor:
            total_time = list(executor.map(lambda _: download(cog, tms, tile_info), range(count)))
        
        average_time = sum(total_time) / count
    else:
        total_time = sum(download(cog, tms, tile_info) for _ in range(count))
        average_time = total_time / count
        
    rounded_average_time = round(average_time)
    print("{:<8} {:<8} {:<12} {:<1}ms".format(tile_info['z'], tile_info['x'], tile_info['y'], rounded_average_time))

def parse_arguments():
    parser = argparse.ArgumentParser(description='Download and benchmark time for tiles from COG.')
    parser.add_argument('-config', type=str, help='Path to JSON configuration file')
    parser.add_argument('-cog', type=str, help='Path to COG file')
    parser.add_argument('-p', action='store_true', help='Get tiles in parallel')
    parser.add_argument('-z', type=int, help='Zoom level')
    parser.add_argument('-x', type=int, help='Tile X coordinate')
    parser.add_argument('-y', type=int, help='Tile Y coordinate')
    parser.add_argument('-c', type=int, help='Amount of times to run')

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_arguments()
    time_start = time.time()

    if args.config:
        with open(args.config, 'r') as config_file:
            config = json.load(config_file)

        cog_path = config["cog"]
        tms_obj = tms.get("WGS1984Quad")

        print("-" * 50)
        print(f"Get tile for {cog_path}")
        print("-" * 50)
        print("{:<8} {:<8} {:<12} {:<1}".format("Z", "X", "Y", "avg (ms)"))
        print("-" * 50)

        for tile_info in config["tiles"]:
            process_tile(cog_path, tms_obj, tile_info, config["count"], args.p)
    else:
        cog_path = args.cog
        tms_obj = tms.get("WGS1984Quad")

        process_tile(cog_path, tms_obj, {'z': args.z, 'x': args.x, 'y': args.y}, args.c, args.p)
        
    print("-" * 50)
    print(f"Total time: {round(time.time() - time_start, 2)}s")
    
