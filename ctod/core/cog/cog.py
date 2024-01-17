from morecantile import TileMatrixSet
from rio_tiler.io import Reader
from rio_tiler.models import ImageData


def download_tile(tms: TileMatrixSet, x: int, y: int, z: int, geotiff_path: str, resampling_method="bilinear") -> ImageData:
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

    with Reader(geotiff_path, tms=tms) as src:     
        image_data = src.tile(tile_z=z, tile_x=x, tile_y=y, resampling_method=resampling_method)
        
        # Set nodata to 0 if nodata is present in the metadata
        nodata_value = src.info().nodata_value if hasattr(src.info(), 'nodata_value') else None

        if nodata_value is not None:
            image_data.data[image_data.data == nodata_value] = float(0)

    return image_data