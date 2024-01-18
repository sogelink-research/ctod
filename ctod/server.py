import asyncio
import logging
import quantized_mesh_encoder.occlusion

from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.factory.terrain_factory import TerrainFactory
from ctod.handlers.index import IndexHandler
from ctod.handlers.layer import LayerJsonHandler
from ctod.handlers.terrain import TerrainHandler
from ctod.core.math import compute_magnitude
from tornado import web

    
def make_server(tile_cache_path: str = None):
    """Create a Tornado web server."""
    
    _patch_occlusion()    
    terrain_factory = TerrainFactory()
    cog_reader_pool = CogReaderPool()

    # Start the periodic cache check in the background
    asyncio.ensure_future(terrain_factory.start_periodic_check())

    return web.Application(
        [
            (r"/", IndexHandler),
            (r"/tiles/layer.json", LayerJsonHandler),
            (
                r"/tiles/(\d+)/(\d+)/(\d+).terrain",
                TerrainHandler,
                dict(
                    terrain_factory=terrain_factory,
                    cog_reader_pool=cog_reader_pool,
                    tile_cache_path=tile_cache_path
                ),
            ),
        ],
        template_path="./ctod/templates",
        static_path="./ctod/templates/static",
        log_function=_log_request,
    )    

def _log_request(handler):
    """Tornado default logs to info, we want it to log to debug"""
    
    logging.debug("%d %s %.2fms",
            handler.get_status(),
            handler._request_summary(),
            1000.0 * handler.request.request_time())
    
def _patch_occlusion():
    """monkey patch quantized_mesh_encoder.occlusion with our own compute_magnitude"""
    
    quantized_mesh_encoder.occlusion.compute_magnitude = compute_magnitude
