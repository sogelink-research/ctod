import logging

from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from ctod.core.terrain.generator.mesh_helper import (
    get_neighbor_files, 
    get_neighbour_transformed_edge_vertices, 
    get_neighbour_normals, 
    average_height_and_normals_to_neighbours)


class TerrainGeneratorQuantizedMeshGrid(TerrainGenerator):
    """A TerrainGenerator for a grid based mesh."""
    
    def __init__(self):
        self.tile_size = 255

    def generate(self, terrain_request: TerrainRequest) -> bytes:
        """Generate a quantized mesh grid based on the terrain request.

        Args:
            terrain_request (TerrainRequest): The terrain request.

        Returns:
            quantized_mesh (bytes): The generated quantized mesh
        """
        
        main_cog = terrain_request.get_main_file()
        
        if main_cog.processed_data is None:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(main_cog.tms, main_cog.z, main_cog.x, main_cog.y)
            return quantized_empty_tile
        
        vertices, triangles, normals, rescaled = main_cog.processed_data

        n, ne, e, se, s, sw, w, nw = get_neighbor_files(terrain_request)
        neighbour_vertices = get_neighbour_transformed_edge_vertices(self.tile_size, n, ne, e, se, s, sw, w, nw)
        neighbour_normals = get_neighbour_normals(self.tile_size, n, ne, e, se, s, sw, w, nw) if terrain_request.generate_normals else None
        
        average_height_and_normals_to_neighbours(vertices, normals, neighbour_vertices, neighbour_normals)
        quantized = quantize(rescaled, triangles, normals)
        
        return quantized