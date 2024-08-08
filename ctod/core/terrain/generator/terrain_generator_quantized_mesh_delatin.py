import logging

from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from ctod.core.utils import rescale_positions
from quantized_mesh_encoder.constants import WGS84
from quantized_mesh_encoder.ellipsoid import Ellipsoid


class TerrainGeneratorQuantizedMeshDelatin(TerrainGenerator):
    """A TerrainGenerator for a delatin based mesh."""

    def __init__(self):
        self.ellipsoid: Ellipsoid = WGS84

    def generate(self, terrain_request: TerrainRequest) -> bytes:
        """Generate a quantized mesh grid based on the terrain request.

        Args:
            terrain_request (TerrainRequest): The terrain request.

        Returns:
            quantized_mesh (bytes): The generated quantized mesh
        """

        main_cog = terrain_request.get_main_file()

        if main_cog is None or main_cog.data is None or main_cog.is_out_of_bounds:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(
                main_cog.tms, main_cog.z, main_cog.x, main_cog.y, main_cog.no_data)
            return quantized_empty_tile

        rescaled_vertices = rescale_positions(
            main_cog.processed_data[0], main_cog.tile_bounds, flip_y=False)
        quantized = quantize(
            rescaled_vertices, main_cog.processed_data[1], main_cog.processed_data[2])

        return quantized
