
import numpy as np

from ctod.core import utils
from ctod.core.cog.processor.grid import generate_grid
from ctod.core.normals import generate_geodetic_normals
from ctod.core.terrain.quantize import quantize
from ctod.core.utils import rescale_positions
from morecantile import TileMatrixSet
from quantized_mesh_encoder.ecef import to_ecef

def generate_empty_tile(tms: TileMatrixSet, z: int, x: int, y: int) -> bytes:
    """Generate an empty terrain tile for a tile index with geodetic surface normals

    Args:
        tms (TileMatrixSet): Tile matrix set to use
        z (int): z tile index
        x (int): x tile index
        y (int): y tile index

    Returns:
        bytes: quantized mesh tile
    """
    
    grid_vertices, grid_triangles = generate_grid(256, 256, 20, 20)
    vertices_3d = np.column_stack((grid_vertices, np.zeros(grid_vertices.shape[0])))
    
    vertices_new = np.array(vertices_3d, dtype=np.float64)
    triangles_new = np.array(grid_triangles, dtype=np.uint16)
    
    bounds = utils.get_tile_bounds(tms, x, y, z)
    rescaled_vertices = rescale_positions(vertices_new, bounds, flip_y=False)
    cartesian = to_ecef(rescaled_vertices)

    normals = generate_geodetic_normals(cartesian, triangles_new)
    quantized = quantize(rescaled_vertices, triangles_new, normals)
        
    return quantized
    