import asyncio
import os
import quantized_mesh_encoder.occlusion

from ctod.core.cog.processor.cog_processor_quantized_mesh_grid import CogProcessorQuantizedMeshGrid
from ctod.core.factory.terrain_factory import TerrainFactory
from ctod.handlers.index import IndexHandler
from ctod.handlers.layer import LayerJsonHandler
from ctod.handlers.terrain import TerrainHandler
from ctod.core.math import compute_magnitude
from tornado import web


def patch_occlusion():
    """monkey patch quantized_mesh_encoder.occlusion with our own compute_magnitude"""
    
    quantized_mesh_encoder.occlusion.compute_magnitude = compute_magnitude
    
def make_server(tile_caching_path: str = None):
    """Create a Tornado web server."""
    
    if not tile_caching_path:
        tile_caching_path = os.environ.get("CTOD_TILE_CACHING_PATH", None)
    
    patch_occlusion()    
    terrain_factory = TerrainFactory()
    cog_processor_mesh_grid = CogProcessorQuantizedMeshGrid()

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
                    cog_processor=cog_processor_mesh_grid,
                    tile_caching_path=tile_caching_path
                ),
            ),
        ],
        template_path="./ctod/templates",
        static_path="./ctod/templates/static",
    )