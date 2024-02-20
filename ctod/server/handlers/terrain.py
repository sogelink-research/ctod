from asyncio import ensure_future
from ctod.core import utils
from fastapi import Response
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.cog.processor.cog_processor_quantized_mesh_grid import (
    CogProcessorQuantizedMeshGrid,
)
from ctod.core.cog.processor.cog_processor_quantized_mesh_delatin import (
    CogProcessorQuantizedMeshDelatin,
)
from ctod.core.cog.processor.cog_processor_quantized_mesh_martini import (
    CogProcessorQuantizedMeshMartini,
)
from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.terrain.empty_tile import generate_empty_tile
from ctod.core.terrain.generator.terrain_generator_quantized_mesh_grid import (
    TerrainGeneratorQuantizedMeshGrid,
)
from ctod.core.terrain.generator.terrain_generator_quantized_mesh_delatin import (
    TerrainGeneratorQuantizedMeshDelatin,
)
from ctod.core.terrain.generator.terrain_generator_quantized_mesh_martini import (
    TerrainGeneratorQuantizedMeshMartini,
)
from ctod.core.tile_cache import get_tile_from_disk, save_tile_to_disk
from morecantile import TileMatrixSet


class TerrainHandler:
    """Handle Cesium terrain requests using a grid based system
    returning quantized mesh tiles.

    Heights and normals are averaged between adjecent tiles to
    create a smooth transition between tiles.
    """

    def __init__(self, terrain_factory, cog_reader_pool, tile_cache_path):
        self.terrain_factory = terrain_factory
        self.tile_cache_path = tile_cache_path
        self.cog_reader_pool = cog_reader_pool
        self.cog_processors = {
            "default": CogProcessorQuantizedMeshGrid,
            "grid": CogProcessorQuantizedMeshGrid,
            "delatin": CogProcessorQuantizedMeshDelatin,
            "martini": CogProcessorQuantizedMeshMartini,
        }
        self.terrain_generators = {
            "default": TerrainGeneratorQuantizedMeshGrid,
            "grid": TerrainGeneratorQuantizedMeshGrid,
            "delatin": TerrainGeneratorQuantizedMeshDelatin,
            "martini": TerrainGeneratorQuantizedMeshMartini,
        }

    async def get(
        self,
        tms,
        z: int,
        x: int,
        y: int,
        cog: str,
        min_zoom: int,
        resampling_method: str,
        meshing_method: str,
        skip_cache: bool,
        processor_options: dict,
        extensions: dict,
    ):
        """Handle a terrain request

        Args:
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index
        """

        x, y, z = utils.tile_index_from_cesium(tms, int(x), int(y), int(z))

        # Try handling the request from the cache
        if not skip_cache:
            cached_tile = self._try_get_cached_tile(cog, meshing_method, z, x, y)
            if cached_tile is not None:
                return Response(
                    content=cached_tile, media_type="application/octet-stream"
                )

        # Always return an empty tile at 0 or requested zoom level is lower than min_zoom
        if z == 0 or z < min_zoom:
            empty_tile = self._return_empty_terrain(tms, cog, meshing_method, z, x, y)
            return Response(content=empty_tile, media_type="application/octet-stream")

        cog_processor = self._get_cog_processor(meshing_method, processor_options)
        terrain_generator = self._get_terrain_generator(meshing_method)
        terrain_request = TerrainRequest(
            tms,
            cog,
            z,
            x,
            y,
            resampling_method,
            cog_processor,
            terrain_generator,
            self.cog_reader_pool,
            extensions["octvertexnormals"],
        )
        quantized = await self.terrain_factory.handle_request(
            tms, terrain_request, self.cog_reader_pool, cog_processor
        )

        self._try_save_tile_to_cache(cog, meshing_method, z, x, y, quantized)

        del terrain_generator
        del cog_processor
        del terrain_request

        return Response(content=quantized, media_type="application/octet-stream")

    def _get_terrain_generator(self, meshing_method: str) -> TerrainGenerator:
        """Get the terrain generator based on the meshing method

        Args:
            meshing_method (str): Meshing method to use

        Returns:
            TerrainGenerator: Terrain generator based on given meshing method
        """

        terrain_generator = self.terrain_generators.get(
            meshing_method, self.terrain_generators["default"]
        )
        return terrain_generator()

    def _get_cog_processor(
        self, meshing_method: str, processor_settings: dict
    ) -> CogProcessor:
        """Get the cog processor based on the meshing method

        Args:
            meshing_method (str): Meshing method to use

        Returns:
            CogProcessor: Cog processor based on given meshing method
        """

        cog_processor = self.cog_processors.get(
            meshing_method, self.cog_processors["default"]
        )
        return cog_processor(processor_settings)

    def _return_empty_terrain(
        self, tms: TileMatrixSet, cog: str, meshing_method: str, z: int, x: int, y: int
    ):
        """Return an empty terrain tile
        generated based on the tile index including geodetic surface normals

        Args:
            tms (TileMatrixSet): The tile matrix set
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index
        """

        quantized_empty_tile = generate_empty_tile(tms, z, x, y)
        self._try_save_tile_to_cache(cog, meshing_method, z, x, y, quantized_empty_tile)
        return quantized_empty_tile

    def _try_get_cached_tile(
        self, cog: str, meshing_method: str, z: int, x: int, y: int
    ) -> bool:
        """Try handling the request from the cache if the path is set

        Args:
            cog (str): Path or url to cog file
            meshing_method (str): The meshing method to use
            resampling_method (str): the resampling method used
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index

        Returns:
            bool: True if the tile was handled from the cache, False otherwise
        """

        if self.tile_cache_path is not None:
            cached_tile = get_tile_from_disk(
                self.tile_cache_path, cog, meshing_method, z, x, y
            )
            if cached_tile is not None:
                return cached_tile

        return None

    def _try_save_tile_to_cache(
        self, cog: str, meshing_method: str, z: int, x: int, y: int, data: bytes
    ):
        """Try saving the tile to the cache if the path is set

        Args:
            cog (str): Path or url to cog file
            meshing_method (str): The meshing method to use
            resampling_method (str): the resampling method used
            z (int): z tile index
            x (int): x tile index
            y (int): y tile index
            data (bytes): bytes of the .terrain tile (quantized mesh)
        """

        if self.tile_cache_path is not None:
            save_tile_to_disk(self.tile_cache_path, cog, meshing_method, z, x, y, data)

    def _write_output(self, output: bytes):
        """Write the output to the response

        Args:
            output (bytes): The output to write to the response
        """

        self.set_header("Content-Type", "application/octet-stream")
        self.write(output)
        self.finish()
