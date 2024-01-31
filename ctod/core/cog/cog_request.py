import asyncio
import time

from ctod.core import utils
from ctod.core.cog.reader.cog_reader import CogReader
from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.utils import generate_cog_cache_key
from functools import partial
from rio_tiler.models import ImageData
from typing import Any


class CogRequest:
    """A request for a Cloud Optimized GeoTIFF tile. 
    COG data is retrieved and processed.
    """
    
    def __init__(self, tms, cog, z, x, y, cog_processor: CogProcessor, cog_reader_pool: CogReaderPool, resampling_method = "bilinear", generate_normals = False):
        self.tms = tms
        self.cog = cog
        self.z = z
        self.x = x
        self.y = y
        self.cog_processor = cog_processor
        self.cog_reader_pool = cog_reader_pool
        self.resampling_method = resampling_method
        self.generate_normals = generate_normals
        self.key = generate_cog_cache_key(cog, z, x, y)
        self.tile_bounds = utils.get_tile_bounds(self.tms, self.x, self.y, self.z)
        self.is_out_of_bounds = False
        self.data = None
        self.processed_data = None
        self.timestamp = time.time()
        self._future = None
    
    def set_data(self, data: ImageData, processed_data: Any, is_out_of_bounds: bool):
        """Set the data manually

        Args:
            data (ImageData): Data from the CogReader
            processed_data (Any): Data processed by the CogProcessor
            is_out_of_bounds (bool): Whether the tile is out of bounds
        """
        
        self.data = data
        self.processed_data = processed_data
        self.is_out_of_bounds = is_out_of_bounds
    
    async def download_tile_async(self):
        """
        Asynchronous version to retrieve an image from a Cloud Optimized GeoTIFF based on a tile index.
        """
        
        loop = asyncio.get_event_loop()
        reader = await self.cog_reader_pool.get_reader(self.cog, self.tms)
        partial_download = partial(self._download, reader, loop)
        future = loop.run_in_executor(None, partial_download)
        return await asyncio.wrap_future(future)

    def _download(self, reader: CogReader, loop):
        kwargs = self.cog_processor.get_reader_kwargs()
        dowloaded_data = reader.download_tile(self.x, self.y, self.z, loop, self.resampling_method, **kwargs)
        
        if dowloaded_data is not None:
            self.data = dowloaded_data
            self.processed_data = self.cog_processor.process(self)
        else:
            self.is_out_of_bounds = True
            
        reader.return_reader()
