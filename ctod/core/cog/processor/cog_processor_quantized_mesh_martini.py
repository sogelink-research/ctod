from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.normals import calculate_normals

from numpy import float32
from pymartini import Martini
from tornado import web
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.ellipsoid import Ellipsoid
from pymartini import rescale_positions

class CogProcessorQuantizedMeshMartini(CogProcessor):
    """A CogProcessor for a Martini based mesh.

    Not working currently, really slow and no shared vertices and normal averaging yet
    """
    
    def __init__(self, request: web.RequestHandler):
        super().__init__()
        self.ellipsoid: Ellipsoid = WGS84
        self._load_settings(request)
        
    def get_reader_kwargs(self):
        return { "buffer": 0.5 }
    
    def process(self, cog_request: CogRequest) -> tuple:
        """Process a CogRequest and return the vertices, triangles and normals created with PyDelatin.

        Args:
            cog_request (CogRequest): The CogRequest to process.

        Returns:
            tuple: vertices, triangles and normals
        """
        
        # According to PyMartini you should reuse the martini object when
        # creating many tiles, however this goes wrong when threading
        # Creating Martini takes aroung 10-100ms
        martini = Martini(cog_request.data.data[0].shape[0]) 
        
        # Create tile is mostly below 100ms but can shoot up to 300ms
        tin = martini.create_tile(cog_request.data.data[0].astype(float32))
        
        # Get mesh looks to be fast
        vertices, triangles = tin.get_mesh(max_error=self._get_max_error(cog_request.z))
        
        rescaled = rescale_positions(vertices, cog_request.data.data[0], bounds=cog_request.data.bounds, flip_y=True)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, triangles) if cog_request.generate_normals else None
        
        return (vertices, triangles, normals)
    
    def _load_settings(self, request: web.RequestHandler):
        """Parse the config

        Args:
            config (dict): The config
        """
        
        self.default_max_error = 5
        self.zoom_max_error = {"15": 5, "16": 3, "17": 2, "18": 1, "19": 0.5, "20": 0.3, "21": 0.2, "22": 0.1}
        
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