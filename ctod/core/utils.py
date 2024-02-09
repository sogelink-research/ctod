import numpy as np
import os

from morecantile import Tile, TileMatrixSet, BoundingBox, tms


def get_dataset_type(file_path: str) -> str:
    """Get the type of dataset based on the file extension.
    ToDo: Use enum
    
    Args:
        file_path (str): Path to the dataset

    Returns:
        str: Type of dataset
    """
    
    _, extension = os.path.splitext(file_path)
    if extension == ".ctod" or extension == ".json":
        return "mosaic"
    elif extension == ".vrt":
        return "vrt"
    else:
        return "cog"
    
def generate_cog_cache_key(cog: str, meshing_method: str, z: int, x: int, y: int) -> str:
    """
    Generate a key for the mesh cache.
    ToDo: cog path should be hashed or something
    """
    
    return f"{cog}_{meshing_method}_{z}_{x}_{y}"

def tile_index_from_cesium(tms: TileMatrixSet, x: int, y: int, z: int) -> tuple[int, int, int]:
    """
    Get correct tile index from a cesium tile index.
    The icoming Cesium tile index is flipped on the Y axis.
    """
    
    tms_y_max = tms.minmax(z)["y"]["max"]
    y = tms_y_max - y
    return x, y, z

def get_tile_bounds(tms: TileMatrixSet, x: int, y: int, z: int) -> BoundingBox:
    """
    Get tile bounds for a given tile index.
    """
    
    tile = Tile(x=x, y=y, z=z)
    return tms.bounds(tile)

def get_neighbor_tiles(tms: TileMatrixSet, x: int, y: int, z: int) -> list[Tile]:
    """
    Get neighbor tiles for a given tile index.
    """
    
    tile = Tile(x=x, y=y, z=z)
    return tms.neighbors(tile)

def get_empty_terrain_path() -> str:
    """
    Get path to an empty terrain tile
    """
    
    empty_terrain_path = "./ctod/files/empty.terrain"
    return empty_terrain_path

def get_tms() -> TileMatrixSet:
    """
    Get the WGS1984Quad TMS which is used in Cesium
    """
    
    return tms.get("WGS1984Quad")

def rescale_positions(
    vertices,
    bounds,
    flip_y: bool = False,
) -> np.ndarray:
    """Rescale positions to bounding box

    Args:
        - vertices: vertices output from Delatin
        - bounds: linearly rescale position values to this extent, expected to
        be [minx, miny, maxx, maxy].
        - flip_y: (bool) Flip y coordinates. Can be useful since images'
        coordinate origin is in the top left.

    Returns:
        (np.ndarray): ndarray of shape (-1, 3) with positions rescaled. Each row
        represents a single 3D point.
    """
    out = np.zeros(vertices.shape, dtype=np.float64)

    tile_size = vertices[:, :2].max()
    minx, miny, maxx, maxy = bounds
    x_scale = (maxx - minx) / tile_size
    y_scale = (maxy - miny) / tile_size

    if flip_y:
        scalar = np.array([x_scale, -y_scale])
        offset = np.array([minx, maxy])
    else:
        scalar = np.array([x_scale, y_scale])
        offset = np.array([minx, miny])

    # Rescale x, y positions
    out[:, :2] = vertices[:, :2] * scalar + offset
    out[:, 2] = vertices[:, 2]
    return out