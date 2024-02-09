import logging

from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from ctod.core.terrain.generator.mesh_helper import (
    average_height_and_normals_to_neighbours,
    merge_shared_vertices, 
    get_neighbor_files,
    get_neighbour_transformed_edge_vertices_from_array, 
    get_neighbour_normals_from_array)
from ctod.core.utils import rescale_positions


class TerrainGeneratorQuantizedMeshMartini(TerrainGenerator):
    """A TerrainGenerator for a martini based mesh."""
    
    def __init__(self):
        self.tile_size = 256

    def generate(self, terrain_request: TerrainRequest) -> bytes:
        """Generate a quantized mesh grid based on the terrain request.

        Args:
            terrain_request (TerrainRequest): The terrain request.

        Returns:
            quantized_mesh (bytes): The generated quantized mesh
        """
        
        main_cog = terrain_request.get_main_file()
        
        # should not happen, in case it does return empty tile
        if main_cog is None or main_cog.data is None or main_cog.is_out_of_bounds:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(main_cog.tms, main_cog.z, main_cog.x, main_cog.y)
            return quantized_empty_tile
        
        n, ne, e, se, s, sw, w, nw = get_neighbor_files(terrain_request)
        
        # remesh neighbours
        n_v, _, n_n = merge_shared_vertices(self.tile_size, n, e=ne, se=e, s=main_cog, sw=w, w=nw)
        ne_v, _, ne_n = merge_shared_vertices(self.tile_size, ne, s=e, sw=main_cog, w=n)
        e_v, _, e_n = merge_shared_vertices(self.tile_size, e, n=ne, s=se, sw=s, w=main_cog, nw=n)
        se_v, _, se_n = merge_shared_vertices(self.tile_size, se, n=e, nw=main_cog, w=s)
        s_v, _, s_n = merge_shared_vertices(self.tile_size, s, e=se, ne=e, n=main_cog, nw=w, w=sw)
        sw_v, _, sw_n = merge_shared_vertices(self.tile_size, sw, e=s, ne=main_cog, n=w)
        w_v, _, w_n = merge_shared_vertices(self.tile_size, w, s=sw, se=s, e=main_cog, ne=n, n=nw)
        nw_v, _, nw_n = merge_shared_vertices(self.tile_size, nw, s=w, e=n, se=main_cog)
        main_v, main_t, main_n = merge_shared_vertices(self.tile_size, main_cog, n=n, ne=ne, e=e, se=se, s=s, sw=sw, w=w, nw=nw)
 
        neighbour_vertices = get_neighbour_transformed_edge_vertices_from_array(self.tile_size, n_v, ne_v, e_v, se_v, s_v, sw_v, w_v, nw_v)
        neighbour_normals = get_neighbour_normals_from_array(self.tile_size, n_v, n_n, ne_v, ne_n, e_v, e_n, se_v, se_n, s_v, s_n, sw_v, sw_n, w_v, w_n, nw_v, nw_n) if terrain_request.generate_normals else None
        average_height_and_normals_to_neighbours(main_v, main_n, neighbour_vertices, neighbour_normals)
        
        rescaled = rescale_positions(main_v, main_cog.tile_bounds, flip_y=False)
        quantized = quantize(rescaled, main_t, main_n)
        
        return quantized
    
