import asyncio
import logging

from ctod.core.cog.dataset_configs import DatasetConfigs
from ctod.core.utils import get_dataset_type
from collections import defaultdict
from ctod.core.cog.reader.cog_reader import CogReader
from ctod.core.cog.reader.cog_reader_mosaic import CogReaderMosaic
from morecantile import TileMatrixSet


class CogReaderPool:
    """Pool to spawn and manage readers for Cloud Optimized GeoTIFFs.
    ToDo: Cleanup readers after being unused for a while, doesn't seem to impact memory usage much.
    """
    
    def __init__(self, unsafe: bool = False, max_readers: int = 0):
        """Create a new pool of readers.

        Args:
            max_readers (int, optional): Amount of max readers in memory per cog path. Defaults to 250.
        """
        
        self.configs = DatasetConfigs()
        self.unsafe = unsafe
        self.max_readers = max_readers
        self.readers = defaultdict(list)
        self.lock = asyncio.Lock()

    async def get_reader(self, cog: str, tms: TileMatrixSet) -> CogReader:
        """Get a reader from the pool. If no reader is available a new one is created.

        Args:
            cog (str): The path/url to the COG
            tms (TileMatrixSet): The TileMatrixSet to use for the COG

        Returns:
            CogReader: A reader for the COG
        """
        
        type = get_dataset_type(cog)

        async with self.lock:
            if cog not in self.readers or len(self.readers[cog]) == 0:
                config = self.configs.get_config(cog)
                
                if type == "mosaic":
                    reader = CogReaderMosaic(self, config, cog, tms, self.unsafe)
                else:
                    reader = CogReader(self, config, cog, tms, self.unsafe)
            else:
                reader = self.readers[cog].pop()

            return reader


    def return_reader(self, reader: CogReader):
        """Return a reader to the pool adding it back to the list of readers for the COG

        Args:
            reader (CogReader): The COG Reader to return to the pool
        """
        
        if(len(self.readers[reader.cog]) >= self.max_readers):
            reader.close()
            del reader
            return
        
        self.readers[reader.cog].append(reader)
        logging.debug(f"Readers in pool for {reader.cog}: {len(self.readers[reader.cog])}")
    
    def populate_pool(self, cog: str, tms: TileMatrixSet, count: int):
        """Populate the pool with readers for a COG

        Args:
            cog (str): The path/url to the COG
            tms (TileMatrixSet): The TileMatrixSet to use for the COG
            count (int): The number of readers to create
        """
        
        for _ in range(count):
            reader = self._create_reader(cog, tms)
            self.return_reader(reader)
    
    def _create_reader(self, cog: str, tms: TileMatrixSet) -> CogReader:
        """Create a new COG Reader for the pool

        Args:
            cog (str): Path/url to the COG
            tms (TileMatrixSet): TileMatrixSet to use for the COG

        Returns:
            reader (CogReader): A new COG Reader
        """
        
        return CogReader(self, cog, tms)