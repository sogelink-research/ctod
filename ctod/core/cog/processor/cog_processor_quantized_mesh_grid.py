import numpy as np

from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ellipsoid import Ellipsoid
from ctod.core.utils import rescale_positions
from ctod.core.cog.processor.grid import generate_grid
from ctod.core.normals import calculate_normals

class CogProcessorQuantizedMeshGrid(CogProcessor):

    def __init__(self):
        self.grid_cache = {}
        self.ellipsoid: Ellipsoid = WGS84
        
    def process(self, cog_request: CogRequest):
        vertices2d, triangles = self.get_grid(25, 25)
        height_data_indices = np.floor(vertices2d).astype(int)
        
        height_data = cog_request.data.data[0][255 - height_data_indices[:, 1], height_data_indices[:, 0]]
        vertices_3d = np.column_stack((vertices2d, height_data))
        
        vertices_new = np.array(vertices_3d, dtype=np.float64)
        triangles_new = np.array(triangles, dtype=np.uint16)
        
        rescaled = rescale_positions(vertices_new, cog_request.tile_bounds, flip_y=False)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, triangles_new) if cog_request.generate_normals else None
        
        return (vertices_new, triangles_new, normals)
                
    def get_grid(self, num_rows, num_cols):
        width, height = 255, 255
        
        if num_rows > height:
            num_rows = height
            
        if num_cols > width:
            num_cols = width

        if (num_rows, num_cols) in self.grid_cache:
            return self.grid_cache[(num_rows, num_cols)]
        
        generated_grid = generate_grid(width, height, num_rows, num_cols)
                
        # Save the generated grid to the cache
        self.grid_cache[(num_rows, num_cols)] = generated_grid

        return generated_grid