import json
import logging
import numpy as np

from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions
from pydelatin import Delatin
from tornado import web
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.ellipsoid import Ellipsoid

class CogProcessorQuantizedMeshDelatin(CogProcessor):
    """A CogProcessor for a Delatin based mesh.

    - Create Delatin mesh
    - Calculate normals
    """
    
    def __init__(self, request: web.RequestHandler):
        super().__init__()
        self.ellipsoid: Ellipsoid = WGS84
        self._load_settings(request)
        
    def process(self, cog_request: CogRequest) -> tuple:
        """Process a CogRequest and return the vertices, triangles and normals created with PyDelatin.

        Args:
            cog_request (CogRequest): The CogRequest to process.

        Returns:
            tuple: vertices, triangles and normals
        """
        
        max_error = self._get_error(cog_request.z)
        tin = Delatin(cog_request.data.data[0], max_error=max_error)
        
        vertices = tin.vertices
        vertices = vertices.reshape(-1, 3).astype('int32')
        
        ## Extract x, y, and z columns
        x = vertices[:, 0].astype(int)
        y = vertices[:, 1].astype(int)
        z = np.round(vertices[:, 2], decimals=4)

        # Combine x, y, and z into a new array
        vertices = np.column_stack((x, y, z))
        
        rescaled = rescale_positions(vertices, cog_request.tile_bounds, flip_y=False)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, tin.triangles) if cog_request.generate_normals else None
        
        return (vertices, tin.triangles, normals)
    
    def _load_settings(self, request: web.RequestHandler):
        """Parse the config

        Args:
            config (dict): The config
        """
        
        self.default_error = int(request.get_argument_ignore_case("defaultGridSize", default=3))
        self.zoom_errors = {"15": 5, "16": 4, "17": 3, "18": 2, "19": 0.7, "20": 0.3, "21": 0.15, "22": 0.1}
        
        zoom_errors_string = request.get_argument_ignore_case("zoomErrors", default=None)
        if zoom_errors_string:
            try:
                self.zoom_errors_string = json.loads(zoom_errors_string)
            except json.JSONDecodeError as e:
                logging.warning("Error parsing zoomErrors:")
    
    def _get_error(self, zoom: int) -> int:
        """Get the grid size for a specific zoom level

        Args:
            zoom (int): The zoom level

        Returns:
            int: The grid size
        """
        
        zoom = str(zoom)
        if self.zoom_errors is not None and zoom in self.zoom_errors:
            return self.zoom_errors[zoom]
        else:
            return self.default_error
