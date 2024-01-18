import asyncio
import time

from ctod.core import utils
from ctod.core.cog.cog import download_tile
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.utils import generate_cog_cache_key
from ctod.core.settings import get_mesh_max_error
from rio_tiler.errors import TileOutsideBounds

class CogRequest:
    def __init__(self, tms, cog, z, x, y, cog_processor: CogProcessor, resampling_method = "bilinear", generate_normals = False):
        self.tms = tms
        self.cog = cog
        self.z = z
        self.x = x
        self.y = y
        self.cog_processor = cog_processor
        self.resampling_method = resampling_method
        self.generate_normals = generate_normals
        self.key = generate_cog_cache_key(cog, z, x, y)
        self.tile_bounds = utils.get_tile_bounds(self.tms, self.x, self.y, self.z)
        self.is_out_of_bounds = False
        self.data = None
        self.processed_data = None
        self.timestamp = time.time()
        # todo: mesh_processor should be defined at query not apriori
        self.flip_y = False # todo: flip if 'martini' in str(self.cog_processor.__class__).lower()?
        self.max_error: float = get_mesh_max_error(self.z)
        self.buffer = 0.0 # todo: 0.5 if 'martini' in str(self.cog_processor.__class__).lower() else 0.0?
        self._future = None
    
    def set_data(self, data, processed_data, is_out_of_bounds):
        self.data = data
        self.processed_data = processed_data
        self.is_out_of_bounds = is_out_of_bounds
    
    async def download_tile_async(self):
        """
        Asynchronous version to retrieve an image from a Cloud Optimized GeoTIFF based on a tile index.
        """
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self._download)
        return await asyncio.wrap_future(future)

    def _download(self):
        try:
            dowloaded_data = download_tile(self.tms, self.x, self.y, self.z, self.cog, self.resampling_method, self.buffer)
            if dowloaded_data is not None:
                self.data = dowloaded_data
                self.processed_data = self.cog_processor.process(self)
            else:
                self.is_out_of_bounds = True
        except TileOutsideBounds:
            self.is_out_of_bounds = True
