import json
import logging
import numpy as np

from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions
from ctod.server.queries import QueryParameters
from pydelatin import Delatin
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.ellipsoid import Ellipsoid

class CogProcessorQuantizedMeshDelatin(CogProcessor):
    """A CogProcessor for a Delatin based mesh.

    - Create Delatin mesh
    - Calculate normals
    """
    
    def __init__(self, qp: QueryParameters):
        super().__init__()
        self.ellipsoid: Ellipsoid = WGS84
        self._load_settings(qp)
        
    def get_name(self) -> str:
        return "delatin"
    
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
    
    def _load_settings(self, qp: QueryParameters):
        """Parse the config

        Args:
            qp (QueryParameters): The quey parameters
        """
        
        self.default_max_error = qp.get_default_max_error()
        self.zoom_max_error = []
             
        zoom_errors_string = qp.get_zoom_max_errors()
        if zoom_errors_string:
            try:
                self.zoom_max_error = json.loads(zoom_errors_string)
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
        if self.zoom_max_error is not None and zoom in self.zoom_max_error:
            return self.zoom_max_error[zoom]
        else:
            return self.default_max_error
