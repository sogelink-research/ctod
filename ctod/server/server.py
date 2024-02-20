import os
import ctod.server.queries as queries

from ctod.core import utils
from ctod.server.helpers import get_extensions
from ctod.args import parse_args, get_value
from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.factory.terrain_factory import TerrainFactory
from ctod.server.handlers.layer import get_layer_json
from ctod.server.handlers.terrain import TerrainHandler
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager


globals = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    args = parse_args()
    unsafe = get_value(args.unsafe, os.environ.get("CTOD_UNSAFE", False), False)
    tile_cache_path = get_value(
        args.tile_cache_path, os.environ.get("CTOD_TILE_CACHE_PATH", None), None
    )

    globals["terrain_factory"] = TerrainFactory()
    globals["terrain_factory"].start_periodic_check()
    globals["cog_reader_pool"] = CogReaderPool(unsafe)
    globals["tile_cache_path"] = tile_cache_path
    globals["tms"] = utils.get_tms()

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
app.mount("/static", StaticFiles(directory="./ctod/templates/static"), name="static")


@app.get(
    "/",
    summary="Open a basic Cesium viewer",
    description="Basic Cesium viewer with a terrain layer to test and debug",
)
async def index():
    return FileResponse("./ctod/templates/index.html")


@app.get(
    "/tiles/layer.json",
    summary="Get the layer.json for a COG",
    description="Get the dynamically generated layer.json for a COG",
    response_class=JSONResponse,
)
def layer_json(
    cog: str = queries.query_cog,
    maxZoom: int = queries.query_max_zoom,
):
    return get_layer_json(globals["tms"], cog, maxZoom)


@app.get(
    "/tiles/{z}/{x}/{y}.terrain",
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
    meshingmethod: str = queries.query_meshing_method,
    skipCache: bool = queries.query_skip_cache,
    defaultGridSize: int = queries.query_default_grid_size,
    zoomGridSizes: str = queries.query_zoom_grid_sizes,
    defaultMaxError: int = queries.query_default_max_error,
    zoomMaxErrors: str = queries.query_zoom_max_errors,
):
    extensions = get_extensions(request)
    processor_options = {
        "defaultGridSize": defaultGridSize,
        "zoomGridSizes": zoomGridSizes,
        "defaultMaxError": defaultMaxError,
        "zoomMaxErrors": zoomMaxErrors,
    }
    th = TerrainHandler(
        terrain_factory=globals["terrain_factory"],
        cog_reader_pool=globals["cog_reader_pool"],
        tile_cache_path=globals["tile_cache_path"],
    )

    return await th.get(
        globals["tms"],
        z,
        x,
        y,
        cog,
        minZoom,
        resamplingMethod,
        meshingmethod,
        skipCache,
        processor_options,
        extensions,
    )
