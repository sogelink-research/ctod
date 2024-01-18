import time

from morecantile import TileMatrixSet
from rio_tiler.io import Reader
from rio_tiler.models import ImageData


class CogReader:
    """A reader for a Cloud Optimized GeoTIFF. This class is used to pool readers to 
    avoid opening and closing the same file many times.
    """
    
    def __init__(self, pool, cog: str, tms: TileMatrixSet):
        self.pool = pool
        self.cog = cog
        self.tms = tms
        self.last_used = time.time()
        self._set_rio_reader()
        self._set_nodata_value()
        
    def close(self):
        """Close the reader."""
        
        self.rio_reader.close()
        
    def download_tile(self, x: int, y: int, z: int, resampling_method="bilinear") -> ImageData:
        """Retrieve an image from a Cloud Optimized GeoTIFF based on a tile index.

        Args:
            tms (TileMatrixSet): The tile matrix set to use.
            x (int): x tile index.
            y (int): y tile index.
            z (int): z tile index.
            geotiff_path (str): Path or URL to the Cloud Optimized GeoTIFF.
            resampling_method (str, optional): RasterIO resampling algorithm. Defaults to "bilinear".

        Returns:
            ImageData: _description_
        """
        
        try:

            image_data = self.rio_reader.tile(tile_z=z, tile_x=x, tile_y=y, resampling_method=resampling_method)
            
            # For now set nodata to 0 if nodata is present in the metadata
            # handle this better later
            if self.nodata_value is not None:
                image_data.data[image_data.data == self.nodata_value] = float(0)

            return image_data
        
        except Exception:
            return None
    
    def return_reader(self):
        """Done with the reader, return it to the pool."""
        
        self.last_used = time.time()
        self.pool.return_reader(self)
        
    def _set_rio_reader(self):
        """Get the reader for the COG."""
        
        self.rio_reader = Reader(self.cog, tms=self.tms)
        
    def _set_nodata_value(self):
        """Set the nodata value for the reader."""
        
        reader_info = self.rio_reader.info()
        self.nodata_value = reader_info.nodata_value if hasattr(reader_info, 'nodata_value') else None
