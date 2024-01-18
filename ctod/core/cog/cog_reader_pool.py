import asyncio
import logging

from collections import defaultdict
from ctod.core.cog.cog_reader import CogReader
from morecantile import TileMatrixSet


class CogReaderPool:
    """Pool to spawn and manage readers for Cloud Optimized GeoTIFFs.
    ToDo: Cleanup readers after being unused for a while, doesn't seem to impact memory usage much.
    """
    
    def __init__(self, max_readers=250):
        """Create a new pool of readers.

        Args:
            max_readers (int, optional): Amount of max readers in memory per cog path. Defaults to 250.
        """
        
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
        
        async with self.lock:
            if cog not in self.readers or len(self.readers[cog]) == 0:
                reader = CogReader(self, cog, tms)
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