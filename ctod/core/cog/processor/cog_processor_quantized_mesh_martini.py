import numpy as np

from pymartini import Martini, rescale_positions as martini_rescale_positions
from pymartini.util import compute_backfill
from quantized_mesh_encoder.ecef import to_ecef
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ellipsoid import Ellipsoid
from ctod.core.cog.cog_request import CogRequest
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.normals import calculate_normals
from ctod.core.utils import rescale_positions


class CogProcessorQuantizedMeshMartini(CogProcessor):

    def __init__(self):
        self.ellipsoid: Ellipsoid = WGS84

    def process(self, cog_request: CogRequest):
        tile = compute_backfill(cog_request.data.data[0].astype(np.float32))
        # todo martini tiles must be 2^n + 1 in size, eg 257x257 not 256x256
        tile_size: int = tile.shape[0]
        martini: Martini = Martini(tile_size)
        tin = martini.create_tile(tile)
        # todo we may want to cache the tile (tin) and call max_error differently
        vertices, triangles = tin.get_mesh(max_error=cog_request.max_error)
        # copied from pymartini rescale positions as weirdly verts is only the 2d positions at this point
        vertices = vertices.reshape(-1, 2).astype(np.float64)
        vertices_new = np.zeros((max(vertices.shape), 3), dtype=np.float64)
        vertices_new[:, :2] = vertices
        vertices_new[:, 2] = tile[vertices[:, 1].astype(np.uint16), vertices[:, 0].astype(np.uint16)]
        # less to do with triangles
        triangles_new = np.array(triangles.reshape(-1, 3), dtype=np.uint32)
        normals = None
        if cog_request.generate_normals:
            rescaled = rescale_positions(vertices_new, cog_request.tile_bounds, flip_y=cog_request.flip_y)
            # todo support other CRSs
            cartesian = to_ecef(rescaled, ellipsoid=self.ellipsoid)
            normals = calculate_normals(cartesian, triangles_new)
        return vertices_new, triangles_new, normals
