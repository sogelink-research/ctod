import asyncio
import logging
import psutil

from concurrent.futures import ThreadPoolExecutor
from ctod.core.cog.cog_request import CogRequest
from ctod.core.terrain.terrain_request import TerrainRequest
from ctod.core.cog.cog_reader_pool import CogReaderPool
from ctod.core.factory.factory_cache import FactoryCache


class TerrainFactory:
    """Factory to handle TerrainRequests

    TerrainFactory has an in memory cache for COG data and a processing queue to prevent
    duplicate requests being send to the COG, this is important when we need adjecent tiles
    for the terrain generation.

    TerrainFactory checks if TerrainRequest are ready for precessing and if so, processes them.
    """

    def __init__(self, cache_path: str, cache_ttl: int = 30):
        self.open_requests = set()
        self.terrain_requests = {}
        self.processing_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.cache = FactoryCache(cache_path, False, ttl=cache_ttl)
        self.pid = psutil.Process().pid
        self.executor = None
        self.cache.on_cache_change(self.cache_changed)
        self.processing_terrain_requests = False
        self.processing_terrain_requests_rerun = False

    async def handle_request(
        self,
        tms,
        terrain_request: TerrainRequest,
        cog_reader_pool: CogReaderPool,
        processor,
    ) -> asyncio.Future:
        """Handle a TerrainRequest

        Args:
            terrain_request (TerrainRequest): Terrain requested trough API

        Returns:
            asyncio.Future: Future which will be set when the terrain is ready
        """
        
        async with self.lock:
            # add terrain_request to terrain_requests cache
            self.terrain_requests[terrain_request.key] = terrain_request

            # loop over wanted files and add to processing queue if needed                
            processing_queue_keys = set(item.key for item in self.processing_queue._queue)
            
            for wanted_file in terrain_request.wanted_files:
                # Check if the cog request is not already in the cache or processing queue or open requests
                if (
                    wanted_file.key not in self.cache.keys
                    and wanted_file.key not in processing_queue_keys
                    and wanted_file.key not in self.open_requests
                ):
                    # Add a new request to the processing queue which handles the download of the cog data
                    cog_request = CogRequest(
                        tms,
                        wanted_file.cog,
                        wanted_file.z,
                        wanted_file.x,
                        wanted_file.y,
                        processor,
                        cog_reader_pool,
                        wanted_file.resampling_method,
                        wanted_file.generate_normals,
                    )

                    await self.processing_queue.put(cog_request)
                    del cog_request

        await self._process_queue()

        # if all wanted files are in the cache: self.cache.keys trigger cache_changed
        # to see if we can directly process the terrain_request
        if set(terrain_request.wanted_file_keys).issubset(self.cache.keys):
            asyncio.create_task(self.cache_changed())

        return await terrain_request.wait()
            
    def start_periodic_check(self, interval: int = 5):
        """Start a task to periodically check the cache for expired items"""

        asyncio.create_task(self.periodic_check(interval))

    async def periodic_check(self, interval: int):
        """Periodically check the cache for expired items

        Args:
            interval (int, optional): The amount of second between checks. Defaults to 5.
        """

        while True:
            await asyncio.sleep(interval)
            await self._cleanup()

    async def _process_queue(self):
        """Process the queue with CogRequests"""

        while not self.processing_queue.empty():
            cog_request = await self.processing_queue.get()
            
            self.open_requests.add(cog_request.key)
            asyncio.create_task(self._process_cog_request(cog_request))
            del cog_request

    async def _process_cog_request(self, cog_request):
        """Process a CogRequest by downloading the data and adding data to the cache"""

        await cog_request.download_tile_async(self._get_executor())
        await self.cache.add(
            cog_request.key,
            {
                "data": cog_request.data,
                "processed_data": cog_request.processed_data,
                "is_out_of_bounds": cog_request.is_out_of_bounds,
            },
        )

        del cog_request

    async def cache_changed(self, keys: list = None):
        """Triggered by the cache when a new item was added"""
        
        # When checking if a cog request is already in cache, open requests
        # when a new requests comes in we need to have it somewhere so we don't directly
        # remove a key from the open_requests until we have it in the cache
        if keys:
            async with self.lock:
                self.open_requests = self.open_requests - set(keys)

        # If already processing the list set rerun to True
        # We don't want to queue since process_terrain_request should pick up 
        # everything that is available for processing
        if self.processing_terrain_requests:
            self.processing_terrain_requests_rerun = True
        else:
            self.processing_terrain_requests = True
            asyncio.create_task(self._process_terrain_requests())

    async def _process_terrain_requests(self):
        """Check and run process on terrain requests when ready for processing"""

        try:            
            # Convert to use O(n) complexity instead of O(n^2) with set intersection
            cache_keys = set(self.cache.keys)
            terrain_keys = list(self.terrain_requests.items())

            # Build a list of keys to get from the cache
            keys_to_get = []
            for key, terrain_request in terrain_keys:
                if terrain_request.processing or terrain_request.result_set:
                    continue

                wanted_keys = set(terrain_request.wanted_file_keys)
                if wanted_keys.issubset(cache_keys):
                    keys_to_get.extend(wanted_keys)

            # Get all items from the cache at once
            cached_items = await self.cache.get(keys_to_get)

            for key, terrain_request in terrain_keys:
                if terrain_request.processing or terrain_request.result_set:
                    continue

                wanted_keys = set(terrain_request.wanted_file_keys)
                if wanted_keys.issubset(cache_keys):
                    for wanted_file in terrain_request.wanted_files:
                        cached_item = cached_items.get(wanted_file.key)
                        if cached_item:
                            wanted_file.set_data(
                                cached_item["data"],
                                cached_item["processed_data"],
                                cached_item["is_out_of_bounds"],
                            )
                        else:
                            wanted_file.set_data(None, None, True)

                    # all data set, ready for processing
                    self.terrain_requests.pop(key, None)
                    asyncio.create_task(terrain_request.process())

            del cache_keys

        except Exception as e:
            logging.error(f"Error processing terrain request: {e}")

        if self.processing_terrain_requests_rerun:
            self.processing_terrain_requests_rerun = False
            asyncio.create_task(self._process_terrain_requests())
        else:
            self.processing_terrain_requests = False

    async def _cleanup(self):
        """Check the cache for expired items and remove them"""

        async with self.lock:
            keep = []
            for _, terrain_request in list(self.terrain_requests.items()):
                for wanted_file in terrain_request.wanted_files:
                    keep.append(wanted_file.key)

            await self.cache.clear_expired(keep)
            if len(self.terrain_requests) == 0:
                self.terrain_requests = {}
                self._try_reset_executor()

        if logging.getLogger().level == logging.DEBUG:
            self._print_debug_info()

    def _get_executor(self):
        """Get the ThreadPoolExecutor"""
        
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=20)

        return self.executor

    def _try_reset_executor(self):
        """
        Try to reset the ThreadPoolExecutor if it's not doing anything
        This is to try to free up memory when idle but seems to have no effect
        but has no negative impact either.
        """
        
        if self.executor and self.executor._work_queue.empty():
            self.executor.shutdown(wait=False)
            self.executor = None

    def _print_debug_info(self):
        """Print debug info about the factory and it's state"""
        
        logging.info(
            f"Factory: terrain reqs: {len(self.terrain_requests)}, cache size: {len(self.cache.keys)}, open requests: {len(self.open_requests)}, queue size: {self.processing_queue.qsize()}"
        )
