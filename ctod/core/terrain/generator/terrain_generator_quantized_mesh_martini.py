import logging

from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from pymartini import rescale_positions

class TerrainGeneratorQuantizedMeshMartini(TerrainGenerator):
    """A TerrainGenerator for a martini based mesh."""
    
    def __init__(self):
        pass

    def generate(self, terrain_request: TerrainRequest) -> bytes:
        """Generate a quantized mesh grid based on the terrain request.

        Args:
            terrain_request (TerrainRequest): The terrain request.

        Returns:
            quantized_mesh (bytes): The generated quantized mesh
        """
        
        main_cog = terrain_request.get_main_file()
        
        # should not happen, in case it does return empty tile
        if main_cog.processed_data is None:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(main_cog.tms, main_cog.z, main_cog.x, main_cog.y)
            return quantized_empty_tile
        
        vertices, triangles, normals = main_cog.processed_data
        rescaled = rescale_positions(vertices, main_cog.data.data[0], bounds=main_cog.data.bounds, flip_y=True)
        quantized = quantize(rescaled, triangles, normals)
        
        return quantized
