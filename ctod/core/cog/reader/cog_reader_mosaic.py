import time
import logging
import asyncio

from morecantile import TileMatrixSet, Tile, BoundingBox
from rio_tiler.mosaic import mosaic_reader
from rio_tiler.models import ImageData
from rio_tiler.errors import TileOutsideBounds
from typing import Any


class CogReaderMosaic:
    """A reader for a Cloud Optimized GeoTIFF. This class is used to pool readers to 
    avoid opening and closing the same file many times.
    """
    
    def __init__(self, pool, config: Any, cog: str, tms: TileMatrixSet, unsafe: bool = False):
        self.pool = pool
        self.config = config
        self.cog = cog
        self.tms = tms
        self.unsafe = unsafe
        self.last_used = time.time()
        
    def close(self):
        """Close the reader."""
        
        self.rio_reader.close()
        
    def tiler(self, src_path: str, *args, **kwargs) -> ImageData:
        future = asyncio.run_coroutine_threadsafe(self.pool.get_reader(src_path, self.tms), args[3])
        reader = future.result()
        
        data = reader.download_tile(args[0], args[1], args[2], args[3], **kwargs)
        reader.return_reader()
                
        if not data:
            raise TileOutsideBounds
            
        return data
        
    def download_tile(self, x: int, y: int, z: int, loop: asyncio.AbstractEventLoop, resampling_method: str = None, **kwargs: Any) -> ImageData:
        """Retrieve an image from a Cloud Optimized GeoTIFF based on a tile index.

        Args:
            tms (TileMatrixSet): The tile matrix set to use.
            x (int): x tile index.
            y (int): y tile index.
            z (int): z tile index.
            loop (asyncio.AbstractEventLoop): The main loop
            resampling_method (str, optional): RasterIO resampling algorithm. Defaults to None.
            kwargs (optional): Options to forward to the `rio_reader.tile` method.

        Returns:
            ImageData: Image data from the Cloud Optimized GeoTIFF.
        """
        
        tile_bounds = self.tms.xy_bounds(Tile(x=x, y=y, z=z))
        datasets = self._get_intersecting_datasets(tile_bounds)
        
        if len(datasets) == 0:
            return None
        
        if not self.unsafe and len(datasets) > 10:
            logging.warning(f"Too many datasets intersecting with requested tile {z,x,y}, {len(datasets)}")
            return None
        
        #logging.info(f"{z} {x} {y} {len(datasets)}\n {datasets} \n {tile_bounds}")
        
        if not self._tile_intersects(tile_bounds, self.config["extent"]) or len(datasets) == 0:
            return None
        
        if resampling_method is not None:
            kwargs["resampling_method"] = resampling_method

        try:
            img, _ = mosaic_reader(datasets, self.tiler, x, y, z, loop, **kwargs)
            return img
        except Exception as e:
            #logging.warning(f"Failed to load tile {self.cog} {z,x,y}, {e}")
            return None   
            
    def return_reader(self):
        """Done with the reader, return it to the pool."""
        
        self.last_used = time.time()
        self.pool.return_reader(self)

    def _get_intersecting_datasets(self, tile_bounds: BoundingBox) -> list:
        intersecting_datasets = []
        for dataset in self.config["datasets"]:
            if self._tile_intersects(tile_bounds, dataset["extent"]):
                intersecting_datasets.append(dataset["path"])
                    
        return intersecting_datasets
                
    def _tile_intersects(self, tile_bounds: BoundingBox, dataset_bounds: list) -> bool:
        """Check if a tile intersects with a dataset.
        Instead of check if inside we check if something is outside and 
        exit early to save some calculation time.

        Args:
            tile_bounds (morecantile.BoundingBox): The bounds of the tile
            dataset_bounds (list): The bounds of the dataset.

        Returns:
            bool: True if bounds intersect, False otherwise
        """
        
        if (tile_bounds.left > dataset_bounds[2] or tile_bounds.right < dataset_bounds[0] or
            tile_bounds.bottom > dataset_bounds[3] or tile_bounds.top < dataset_bounds[1]):
            return False
        
        return True
