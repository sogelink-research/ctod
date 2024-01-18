import numpy as np

from pydelatin import Delatin
from pydelatin.util import rescale_positions as delatin_rescale_positions
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ellipsoid import Ellipsoid
from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions

class CogProcessorQuantizedMeshDelatin(CogProcessor):

    def __init__(self):
        self.encoder_cache = {}
        self.ellipsoid: Ellipsoid = WGS84

    def process(self, cog_request: CogRequest):
        tile = cog_request.data.data[0]
        tile_size: int = tile.shape[0]
        tin = Delatin(tile, height=tile_size, width=tile_size, max_error=cog_request.max_error)
        vertices_new = tin.vertices.astype(np.float64)
        triangles_new = np.array(tin.triangles, dtype=np.uint32)  # in case we have more than 65536 vertices
        normals = None
        if cog_request.generate_normals:
            rescaled = rescale_positions(vertices_new, cog_request.tile_bounds, flip_y=cog_request.flip_y)
            # todo support other CRSs
            cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
            normals = calculate_normals(cartesian, triangles_new)
        return vertices_new, triangles_new, normals
