import asyncio
import time

from morecantile import TileMatrixSet
from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.cog.processor.cog_processor import CogProcessor
from ctod.core.cog.cog_request import CogRequest
from ctod.core.terrain.generator.terrain_generator import TerrainGenerator
from ctod.core.utils import (
    get_neighbor_tiles,
    generate_uuid,
    generate_cog_cache_key,
)
from ctod.core.direction import Direction, move_in_direction


class TerrainRequest:
    """Request for a terrain tile"""

    def __init__(
        self,
        tms: TileMatrixSet,
        cog: str,
        z: int,
        x: int,
        y: int,
        resampling_method: str,
        cog_processor: CogProcessor,
        terrain_generator: TerrainGenerator,
        cog_reader_pool: CogReaderPool,
        generate_normals=False,
    ):
        self.tms = tms
        self.cog = cog
        self.z = z
        self.x = x
        self.y = y
        self.resampling_method = resampling_method
        self.cog_processor = cog_processor
        self.terrain_generator = terrain_generator
        self.generate_normals = generate_normals
        self.cog_reader_pool = cog_reader_pool
        self.wanted_files = []
        self._generate_wanted_files()
        self.key = generate_uuid()
        self.main_file_key = generate_cog_cache_key(self.cog, self.cog_processor.get_name(), self.z, self.x, self.y)
        self.wanted_file_keys = self.get_wanted_file_keys()
        self.processing = False
        self.future = asyncio.Future()
        self.result_set = False
        self.request_time = time.time()

    def get_main_file(self) -> CogRequest:
        """Get the main CogRequest for this TerrainRequest

        Returns:
            CogRequest: The main CogRequest for this TerrainRequest
        """

        return self.get_file(self.main_file_key)

    def get_neighbour_file(self, direction: Direction) -> CogRequest:
        """Get the CogRequest for the neighbour file in the given direction

        Args:
            direction (Direction): Get the neighbour file in this direction

        Returns:
            CogRequest: The CogRequest for the neighbour file in the given direction
        """

        x, y = move_in_direction(self.x, self.y, direction)
        key = generate_cog_cache_key(
            self.cog, self.cog_processor.get_name(), self.z, x, y
        )
        return self.get_file(key)

    def get_file(self, key: str) -> CogRequest:
        """Get the CogRequest for the given key

        Args:
            key (str): The key of the CogRequest to get

        Returns:
            CogRequest: The CogRequest for the given key
        """
        import logging

        logging.basicConfig(level=logging.DEBUG)

        for wanted_file in self.wanted_files:
            if wanted_file.key == key:
                logging.debug(f"Found file for key: {key}")
                return wanted_file

        logging.error(f"File not found for key: {key}")
        return None

    def get_wanted_file_keys(self) -> list:
        """Get the keys of the wanted files

        Returns:
            list: The keys of the wanted files
        """

        return [wanted_file.key for wanted_file in self.wanted_files]

    def has_all_data(self) -> bool:
        """Check if all data is available to process the terrain tile

        Returns:
            bool: true if all data is available and ready for processing
        """

        for wanted_file in self.wanted_files:
            if (
                wanted_file.data is None or wanted_file.processed_data is None
            ) and wanted_file.is_out_of_bounds == False:
                return False

        return True

    async def process(self):
        """Start processing the terrain tile"""
        import logging

        logging.basicConfig(level=logging.DEBUG)

        if self.processing or self.result_set:
            return

        self.processing = True
        logging.debug(f"Processing started for tile: z={self.z}, x={self.x}, y={self.y}")
        result = self.terrain_generator.generate(self)
        self.set_result(result)
        logging.debug(f"Processing completed for tile: z={self.z}, x={self.x}, y={self.y}")
        self.processing = False

    def set_timed_out(self):
        """Set the TerrainRequest to timed out"""

        self.set_exception(Exception("Timed out"))

    def set_result(self, result: bytes):
        """Set the result of the terrain tile

        Args:
            bytes: Terrain data
        """

        self.future.set_result(result)
        self.result_set = True

    def set_exception(self, exception: BaseException):
        """Set the exception of the terrain tile

        Args:
            exception (BaseException): Exception to set
        """

        self.future.set_exception(exception)
        self.result_set = True

    async def wait(self) -> asyncio.Future:
        """Wait for the result of the TerrainRequest

        Returns:
            asyncio.Future: result
        """

        return await self.future

    def _generate_wanted_files(self):
        """Generate the wanted files for this TerrainRequest
        which are the adjacent tiles and the main tile
        """
        import logging

        logging.basicConfig(level=logging.DEBUG)
        
        # Add the main tile
        self.wanted_files.append(
            CogRequest(
                self.tms,
                self.cog,
                self.z,
                self.x,
                self.y,
                self.cog_processor,
                self.cog_reader_pool,
                self.resampling_method,
                self.generate_normals,
            )
        )
        logging.debug(f"Added main tile: z={self.z}, x={self.x}, y={self.y}")

        # Add neighbor tiles
        neighbour_tiles = get_neighbor_tiles(self.tms, self.x, self.y, self.z)
        for tile in neighbour_tiles:
            self.wanted_files.append(
                CogRequest(
                    self.tms,
                    self.cog,
                    tile.z,
                    tile.x,
                    tile.y,
                    self.cog_processor,
                    self.cog_reader_pool,
                    self.resampling_method,
                    self.generate_normals,
                )
            )
            logging.debug(f"Added neighbor tile: z={tile.z}, x={tile.x}, y={tile.y}")

        # Ensure level 0 tiles are included
        if self.z == 0:
            for x in range(2):
                for y in range(1):
                    self.wanted_files.append(
                        CogRequest(
                            self.tms,
                            self.cog,
                            0,
                            x,
                            y,
                            self.cog_processor,
                            self.cog_reader_pool,
                            self.resampling_method,
                            self.generate_normals,
                        )
                    )
                    logging.debug(f"Added level 0 tile: z=0, x={x}, y={y}")
