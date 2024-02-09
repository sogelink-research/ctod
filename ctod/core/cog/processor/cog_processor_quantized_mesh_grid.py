import json
import logging
import numpy as np

from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.cog.processor.grid import generate_grid
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions
from tornado import web
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.ellipsoid import Ellipsoid


class CogProcessorQuantizedMeshGrid(CogProcessor):
    """A CogProcessor for a grid based mesh.
    
    - Create grid with 2d vertices and triangles
    - Sample height data from COG data and make vertices 3d
    - Calculate normals
    
    ToDo: Grids can be stored in a cache, however generating a grid takes 0.7ms on average
    """

    def __init__(self, request: web.RequestHandler):
        super().__init__()
        self.grid_wh = 255
        self.ellipsoid: Ellipsoid = WGS84
        self._load_settings(request)
    
    def get_name(self) -> str:
        return "grid"
    
    def process(self, cog_request: CogRequest) -> tuple:
        """Process a CogRequest and return the vertices, triangles and normals.

        Args:
            cog_request (CogRequest): The CogRequest to process.

        Returns:
            tuple: Generated vertices, triangles and normals
        """
        
        grid_size = self._get_grid_size(cog_request.z)
        vertices2d, triangles = self._get_grid(grid_size, grid_size)
        height_data_indices = np.floor(vertices2d).astype(int)
        
        height_data = cog_request.data.data[0][255 - height_data_indices[:, 1], height_data_indices[:, 0]]
        vertices_3d = np.column_stack((vertices2d, height_data))
        
        vertices_new = np.array(vertices_3d, dtype=np.float64)
        triangles_new = np.array(triangles, dtype=np.uint16)
        
        rescaled = rescale_positions(vertices_new, cog_request.tile_bounds, flip_y=False)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, triangles_new) if cog_request.generate_normals else None
        
        return (vertices_new, triangles_new, normals, rescaled)

    def _load_settings(self, request: web.RequestHandler):
        """Parse the config

        Args:
            config (dict): The config
        """
        
        self.default_grid_size = int(request.get_argument_ignore_case("defaultGridSize", default=20))
        self.zoom_grid_sizes = {"15": 25, "16": 25, "17": 30, "18": 35, "19": 35, "20": 35, "21": 35, "22": 35}
        
        zoomGridSizesString = request.get_argument_ignore_case("zoomGridSizes", default=None)
        if zoomGridSizesString:
            try:
                self.zoom_grid_sizes = json.loads(zoomGridSizesString)
            except json.JSONDecodeError as e:
                logging.warning("Error parsing zoomGridSizes:")
    
    def _get_grid_size(self, zoom: int) -> int:
        """Get the grid size for a specific zoom level

        Args:
            zoom (int): The zoom level

        Returns:
            int: The grid size
        """
        
        zoom = str(zoom)
        if self.zoom_grid_sizes is not None and zoom in self.zoom_grid_sizes:
            return self.zoom_grid_sizes[zoom]
        else:
            return self.default_grid_size
        
    def _get_grid(self, num_rows: int, num_cols: int) -> tuple:
        """Generate a grid of vertices and triangles

        Args:
            num_rows (int): Amount of rows to generate
            num_cols (int): Amount of columns to generate

        Returns:
            tuple: vertices, triangles
        """
        
        if num_rows > self.grid_wh:
            num_rows = self.grid_wh
            
        if num_cols > self.grid_wh:
            num_cols = self.grid_wh

        generated_grid = generate_grid(self.grid_wh, self.grid_wh, num_rows, num_cols)
                
        return generated_grid
  