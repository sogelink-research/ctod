import time

from rio_tiler.io import COGReader

def download_tile(tms, x, y, z, geotiff_path, resampling_method="bilinear"):
    """
    Retrieve an image from a Cloud Optimized GeoTIFF based on a tile index.
    """

    with COGReader(geotiff_path, tms=tms) as src:     
        data = src.tile(tile_z=z, tile_x=x, tile_y=y, resampling_method=resampling_method)
        
        # Set nodata to 0 if nodata is present in the metadata
        nodata = src.info().nodata_value if hasattr(src.info(), 'nodata_value') else None

        if nodata is not None:
            data.data[data.data == nodata] = float(0)

    return data