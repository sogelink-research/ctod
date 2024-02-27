import json
import logging
import numpy as np

from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from numpy import float32
from ctod.server.queries import QueryParameters
from pymartini import Martini
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ellipsoid import Ellipsoid


class CogProcessorQuantizedMeshMartini(CogProcessor):
    """A CogProcessor for a Martini based mesh.

    Not working currently, really slow and no shared vertices and normal averaging yet
    """
    
    def __init__(self, qp: QueryParameters):
        super().__init__()
        self.ellipsoid: Ellipsoid = WGS84
        self._load_settings(qp)
        
    def get_reader_kwargs(self):
        return { "buffer": 0.5 }
    
    def get_name(self) -> str:
        return "martini"
    
    def process(self, cog_request: CogRequest) -> tuple:
        """Process a CogRequest and return the vertices, triangles and normals created with PyDelatin.

        Args:
            cog_request (CogRequest): The CogRequest to process.

        Returns:
            tuple: vertices, triangles and normals
        """
        
        tile_size = 256
        
        # According to PyMartini you should reuse the martini object when
        # Creating many tiles, however this goes wrong when threading
        # Creating Martini takes aroung 10-100ms
        martini = Martini(cog_request.data.data[0].shape[0]) 
        
        # Create tile is mostly below 100ms but can shoot up to 300ms
        tin = martini.create_tile(cog_request.data.data[0].astype(float32))
        
        # Get mesh looks to be fast
        vertices, triangles = tin.get_mesh(max_error=self._get_max_error(cog_request.z))
        
        # Reshape and flip y
        vertices = vertices.reshape(-1, 2)
        vertices[:, 1] = tile_size - vertices[:, 1]
        
        # Add height data
        height_data_indices = np.floor(vertices).astype(int)   
        height_data = cog_request.data.data[0][tile_size - height_data_indices[:, 1], height_data_indices[:, 0]]
        new_vertices = np.column_stack((vertices, height_data))
        
        return (new_vertices, triangles, None)
    
    def _load_settings(self, qp: QueryParameters):
        """Parse the config

        Args:
            qp (QueryParameters): The query parameters
        """
        
        self.default_max_error = qp.get_default_max_error()   
        self.zoom_max_error = []
        zoom_errors_string = qp.get_zoom_max_errors()

        if zoom_errors_string:
            try:
                self.zoom_max_error = json.loads(zoom_errors_string)
            except json.JSONDecodeError as e:
                logging.warning("Error parsing zoomErrors:")

    def _get_max_error(self, zoom: int) -> int:
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