from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions
from pydelatin import Delatin
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.ellipsoid import Ellipsoid

class CogProcessorQuantizedMeshDelatin(CogProcessor):
    """A CogProcessor for a Delatin based mesh.

    - Create Delatin mesh
    - Calculate normals
    """
    
    def __init__(self):
        self.ellipsoid: Ellipsoid = WGS84
        
    def process(self, cog_request: CogRequest) -> tuple:
        """Process a CogRequest and return the vertices, triangles and normals created with PyDelatin.

        Args:
            cog_request (CogRequest): The CogRequest to process.

        Returns:
            tuple: vertices, triangles and normals
        """
        
        tin = Delatin(cog_request.data.data[0], max_error=1)
        rescaled = rescale_positions(tin.vertices, cog_request.tile_bounds, flip_y=False)
        cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
        normals = calculate_normals(cartesian, tin.triangles) if cog_request.generate_normals else None
        
        return (tin.vertices, tin.triangles, normals)