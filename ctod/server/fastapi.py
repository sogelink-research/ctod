import os
import ctod.server.queries as queries
import logging

from datetime import datetime, timezone
from fastapi.templating import Jinja2Templates
from ctod.config.dataset_config import DatasetConfig
from ctod.server.handlers.status import get_server_status
from ctod.core import utils
from ctod.server.helpers import get_extensions
from ctod.args import parse_args, get_value
from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.factory.terrain_factory import TerrainFactory
from ctod.server.handlers.layer import get_layer_json
from ctod.server.handlers.terrain import TerrainHandler
from ctod.server.startup import patch_occlusion, setup_logging, log_ctod_start
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager


globals = {}
current_dir = os.path.dirname(os.path.abspath(__file__))
path_static_files = os.path.join(current_dir, "../templates/preview")
path_template_files = os.path.join(current_dir, "../templates")
templates = Jinja2Templates(directory=path_template_files)


@asynccontextmanager
async def lifespan(app: FastAPI):
    args = parse_args()
    unsafe = get_value(args, "unsafe", os.environ.get(
        "CTOD_UNSAFE", False), False)

    no_dynamic = get_value(args, "no_dynamic", os.environ.get(
        "CTOD_NO_DYNAMIC", False), False)

    tile_cache_path = get_value(
        args, "tile_cache_path", os.environ.get(
            "CTOD_TILE_CACHE_PATH", None), None
    )

    port = get_value(args, "port", int(
        os.environ.get("CTOD_PORT", 5000)), 5000)

    logging_level = get_value(
        args, "logging_level", os.environ.get(
            "CTOD_LOGGING_LEVEL", "info"), "info"
    )

    db_name = get_value(
        args, "db_name", os.environ.get(
            "CTOD_DB_NAME", "factory_cache.db"), "factory_cache.db"
    )

    factory_cache_ttl = 15

    dataset_config_path = get_value(
        args, "dataset_config_path", os.environ.get(
            "CTOD_DATASET_CONFIG_PATH", "./config/datasets.json"), "./config/datasets.json"
    )

    patch_occlusion()
    setup_logging(log_level=getattr(logging, logging_level.upper()))
    log_ctod_start(port, tile_cache_path)

    dataset_config = DatasetConfig(dataset_config_path)
    terrain_factory = TerrainFactory(
        tile_cache_path, db_name, factory_cache_ttl)
    await terrain_factory.cache.initialize()

    globals["terrain_factory"] = terrain_factory
    globals["terrain_factory"].start_periodic_check()
    globals["cog_reader_pool"] = CogReaderPool(unsafe)
    globals["tile_cache_path"] = tile_cache_path
    globals["no_dynamic"] = no_dynamic
    globals["dataset_config"] = dataset_config
    globals["tms"] = utils.get_tms()
    globals["start_time"] = datetime.now(timezone.utc)

    yield


app = FastAPI(
    lifespan=lifespan,
    title="CTOD",
    description="Cesium Terrain On Demand",
    summary="CTOD fetches Cesium terrain tiles from Cloud Optimized GeoTIFFs dynamically, avoiding extensive caching to save time and storage space. By generating tiles on demand, it optimizes efficiency and reduces resource consumption compared to traditional caching methods.",
    version="0.9.0",
    debug=False,
)

# Mount the static files directory to serve the Cesium viewer
app.mount("/preview", StaticFiles(directory=path_static_files), name="preview")


@app.get(
    "/",
    summary="Open a basic Cesium viewer",
    description="Basic Cesium viewer with a terrain layer to test and debug",
)
async def index(request: Request):
    dataset_names = globals["dataset_config"].get_dataset_names()
    links = [{"name": name, "url": f"./preview/index.html?dataset={name}"}
             for name in dataset_names]

    dynamic = {"name": "dynamic", "url": "./preview/index.html"}
    if globals["no_dynamic"]:
        dynamic = None

    status = get_server_status(globals["start_time"])

    return templates.TemplateResponse("index.html", {"request": request, "links": links, "dynamic": dynamic, "status": status})


@app.get(
    "/status",
    summary="Get the status of the server",
    description="Get the start time and uptime of the server",
    response_class=JSONResponse,
)
def status():
    """Return the server status"""
    return get_server_status(globals["start_time"])


@app.get(
    "/tiles/dynamic/layer.json",
    summary="Get the layer.json for a COG",
    description="Get the dynamically generated layer.json for a COG",
    response_class=JSONResponse,
)
def layer_json(
    cog: str = queries.query_cog,
    minZoom: int = queries.query_min_zoom,
    maxZoom: int = queries.query_max_zoom,
    resamplingMethod: str = queries.query_resampling_method,
    meshingMethod: str = queries.query_meshing_method,
    skipCache: bool = queries.query_skip_cache,
    defaultGridSize: int = queries.query_default_grid_size,
    zoomGridSizes: str = queries.query_zoom_grid_sizes,
    defaultMaxError: int = queries.query_default_max_error,
    zoomMaxErrors: str = queries.query_zoom_max_errors,
    extensions: str = queries.query_extensions,
    noData: int = queries.query_no_data
):
    if globals["no_dynamic"]:
        return JSONResponse(status_code=404, content={"message": "Dynamic tiles are disabled"})

    params = queries.QueryParameters(
        cog,
        minZoom,
        maxZoom,
        resamplingMethod,
        meshingMethod,
        skipCache,
        defaultGridSize,
        zoomGridSizes,
        defaultMaxError,
        zoomMaxErrors,
        extensions,
        noData
    )

    return get_layer_json(globals["tms"], params)


@app.get(
    "/tiles/{dataset}/layer.json",
    summary="Get the layer.json for a COG",
    description="Get the dynamically generated layer.json for a COG",
    response_class=JSONResponse,
)
def layer_json(
    dataset: str,
):
    queryParams = globals["dataset_config"].get_dataset(dataset)
    if queryParams is None:
        return JSONResponse(status_code=404, content={"message": "Dataset not found"})

    return get_layer_json(globals["tms"], queryParams)


@app.get(
    "/tiles/dynamic/{z}/{x}/{y}.terrain",
    summary="Get a terrain tile",
    description="Generates and returns a terrain tile from a COG",
    response_class=FileResponse,
)
async def terrain(
    request: Request,
    z: int,
    x: int,
    y: int,
    cog: str = queries.query_cog,
    minZoom: int = queries.query_min_zoom,
    resamplingMethod: str = queries.query_resampling_method,
    meshingMethod: str = queries.query_meshing_method,
    skipCache: bool = queries.query_skip_cache,
    defaultGridSize: int = queries.query_default_grid_size,
    zoomGridSizes: str = queries.query_zoom_grid_sizes,
    defaultMaxError: int = queries.query_default_max_error,
    zoomMaxErrors: str = queries.query_zoom_max_errors,
    extensions: str = queries.query_extensions,
    noData: int = queries.query_no_data
):
    if globals["no_dynamic"]:
        return JSONResponse(status_code=404, content={"message": "Dynamic tiles are disabled"})

    params = queries.QueryParameters(
        cog,
        minZoom,
        None,
        resamplingMethod,
        meshingMethod,
        skipCache,
        defaultGridSize,
        zoomGridSizes,
        defaultMaxError,
        zoomMaxErrors,
        extensions,
        noData
    )

    use_extensions = get_extensions(extensions, request)

    th = TerrainHandler(
        terrain_factory=globals["terrain_factory"],
        cog_reader_pool=globals["cog_reader_pool"],
        tile_cache_path=globals["tile_cache_path"],
    )

    return await th.get(
        request,
        globals["tms"],
        z,
        x,
        y,
        params,
        use_extensions,
    )


@app.get(
    "/tiles/{dataset}/{z}/{x}/{y}.terrain",
    summary="Get a terrain tile",
    description="Generates and returns a terrain tile from a COG",
    response_class=FileResponse,
)
async def terrain(
    request: Request,
    dataset: str,
    z: int,
    x: int,
    y: int,
):
    queryParams = globals["dataset_config"].get_dataset(dataset)
    if queryParams is None:
        return JSONResponse(status_code=404, content={"message": "Dataset not found"})

    use_extensions = get_extensions(queryParams.get_extensions(), request)

    th = TerrainHandler(
        terrain_factory=globals["terrain_factory"],
        cog_reader_pool=globals["cog_reader_pool"],
        tile_cache_path=globals["tile_cache_path"],
    )

    return await th.get(
        request,
        globals["tms"],
        z,
        x,
        y,
        queryParams,
        use_extensions,
    )
