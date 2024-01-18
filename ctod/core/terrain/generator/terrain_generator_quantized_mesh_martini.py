import logging
import numpy as np

from ctod.core.cog.cog_request import CogRequest

from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.quantize import quantize
from ctod.core.direction import Direction
from ctod.core.utils import rescale_positions
from ctod.core.terrain.empty_tile import generate_empty_tile

from .terrain_generator_quantized_mesh_grid import TerrainGeneratorQuantizedMeshGrid


class TerrainGeneratorQuantizedMeshMartini(TerrainGeneratorQuantizedMeshGrid):
    def generate(self, terrain_request: TerrainRequest):
        main_cog = terrain_request.get_main_file()

        # should not happen, in case it does return empty tile
        if main_cog.processed_data is None:
            logging.debug("main_cog.processed_data is None")
            quantized_empty_tile = generate_empty_tile(main_cog.tms, main_cog.z, main_cog.x, main_cog.y)
            return quantized_empty_tile

        vertices, triangles, normals = main_cog.processed_data

        # todo: Martini tiles are a bit strange to work with so some more thought is needed here

        # Rescale the vertices to the tile bounds and create quantized mesh
        rescaled_vertices = rescale_positions(vertices, main_cog.tile_bounds, flip_y=False)
        quantized = quantize(rescaled_vertices, triangles, normals)

        return quantized

