import os
import ctod.server.queries as queries
import logging

from datetime import datetime, timezone
from fastapi.templating import Jinja2Templates
from ctod.config.dataset_config import DatasetConfig
from ctod.server.handlers.status import get_server_status
from ctod.core import utils
from ctod.server.helpers import get_extensions
from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.factory.terrain_factory import TerrainFactory
from ctod.server.handlers.layer import get_layer_json
from ctod.server.handlers.terrain import TerrainHandler
from ctod.server.settings import Settings
from ctod.server.startup import patch_occlusion, setup_logging, log_ctod_start
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


globals = {}
current_dir = os.path.dirname(os.path.abspath(__file__))
path_static_files = os.path.join(current_dir, "../templates/preview")
path_template_files = os.path.join(current_dir, "../templates")
templates = Jinja2Templates(directory=path_template_files)
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    patch_occlusion()
    setup_logging(log_level=getattr(logging, settings.logging_level.upper()))
    log_ctod_start(settings)
    await setup_globals(settings)

    yield


async def setup_globals(settings: Settings):
    dataset_config = DatasetConfig(settings.dataset_config_path)
    terrain_factory = TerrainFactory(
        settings.tile_cache_path, settings.db_name, settings.factory_cache_ttl)
    await terrain_factory.cache.initialize()

    globals["terrain_factory"] = terrain_factory
    globals["terrain_factory"].start_periodic_check()
    globals["cog_reader_pool"] = CogReaderPool(settings.unsafe)
    globals["tile_cache_path"] = settings.tile_cache_path
    globals["no_dynamic"] = settings.no_dynamic
    globals["dataset_config"] = dataset_config
    globals["tms"] = utils.get_tms()
    globals["start_time"] = datetime.now(timezone.utc)


app = FastAPI(
    lifespan=lifespan,
    title="CTOD",
    description="Cesium Terrain On Demand",
    summary="CTOD fetches Cesium terrain tiles from Cloud Optimized GeoTIFFs dynamically, avoiding extensive caching to save time and storage space. By generating tiles on demand, it optimizes efficiency and reduces resource consumption compared to traditional caching methods.",
    version="1.0.1",
    debug=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
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
