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

    def __init__(self, cache_expiry_seconds=30):
        self.cache_expiry_seconds = cache_expiry_seconds
        self.open_requests = set()
        self.terrain_requests = {}
        self.processing_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.cache = FactoryCache(False, ttl=cache_expiry_seconds)
        self.pid = psutil.Process().pid
        self.executor = None
        self.cache.on_set(self.cache_on_set)

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
            processing_queue_keys = set(
                item[0].key for item in self.processing_queue._queue
            )
            open_requests_keys = set(self.open_requests)

            for wanted_file in terrain_request.wanted_files:
                # Check if the data is already available in the cache
                if wanted_file.key not in self.cache.keys:
                    if (
                        wanted_file.key not in processing_queue_keys
                        and wanted_file.key not in open_requests_keys
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

                        await self.processing_queue.put((cog_request,))
                        del cog_request

        await self._process_queue()

        # if all wanted files are in the cache: self.cache.keys, process the terrain request
        if set(terrain_request.wanted_file_keys).issubset(self.cache.keys):
            await self._process_terrain_requests()

        return await terrain_request.wait()

    def start_periodic_check(self, interval: int = 5):
        asyncio.create_task(self.periodic_check(interval))

    async def periodic_check(self, interval: int = 5):
        """Periodically check the cache for expired items

        Args:
            interval (int, optional): The amount of second between checks. Defaults to 5.
        """

        while True:
            await asyncio.sleep(interval)
            await self._cleanup()

    async def _process_queue(self):
        """Process the queue with CogRequests"""

        async with self.lock:
            while not self.processing_queue.empty():
                (cog_request,) = await self.processing_queue.get()
                self.open_requests.add(cog_request.key)
                asyncio.create_task(self._process_completed_cog_request(cog_request))
                del cog_request

    async def _process_completed_cog_request(self, cog_request):
        try:
            async with self.lock:
                await cog_request.download_tile_async(self._get_executor())
                if cog_request:
                    self.open_requests.remove(cog_request.key)

            await self.cache.set(
                cog_request.key,
                {
                    "data": cog_request.data,
                    "processed_data": cog_request.processed_data,
                    "is_out_of_bounds": cog_request.is_out_of_bounds,
                },
            )
            del cog_request

        except Exception as e:
            logging.error(f"Error processing completed cog request: {e}")

    async def _handle_cancelled_request(self, terrain_request: TerrainRequest):
        """Handle a cancelled TerrainRequest

        Args:
            terrain_request (TerrainRequest): Terrain requested trough API
        """

        async with self.lock:
            # remove terrain_request from terrain_requests cache
            if terrain_request.key in self.terrain_requests:
                del self.terrain_requests[terrain_request.key]

            # loop over wanted files in queue and remove if not in wanted files for every terrain_request in self.terrain_requests
            for wanted_file in list(self.processing_queue._queue):
                if wanted_file[0].key not in [
                    wanted_file.key
                    for terrain_request in self.terrain_requests.values()
                    for wanted_file in terrain_request.wanted_files
                ]:
                    self.processing_queue._queue.remove(wanted_file)
                if wanted_file[0].key in self.open_requests:
                    self.open_requests.remove(wanted_file[0].key)

    async def cache_on_set(self, key):
        """Triggered by the cache when a new item was added"""

        await self._process_terrain_requests()

    async def _process_terrain_requests(self):
        """Check and run process on terrain requests when ready for processing"""

        async with self.lock:
            keys_to_remove = []
            temp_cache = {}

            try:
                # Convert to use O(n) complexity instead of O(n^2) with set intersection
                cache_keys = set(self.cache.keys)

                for key, terrain_request in list(self.terrain_requests.items()):
                    wanted_keys = set(terrain_request.wanted_file_keys)

                    # if all wanted files are in the cache, process the terrain request
                    if wanted_keys.issubset(cache_keys):
                        for wanted_file in terrain_request.wanted_files:

                            # Temporary in-memory cache to prevent accessing database
                            # and running pickle.loads multiple times
                            if wanted_file.key not in temp_cache:
                                cached_item = self.cache.get(wanted_file.key)
                                temp_cache[wanted_file.key] = cached_item
                            else:
                                cached_item = temp_cache[wanted_file.key]

                            if cached_item:
                                wanted_file.set_data(
                                    cached_item["data"],
                                    cached_item["processed_data"],
                                    cached_item["is_out_of_bounds"],
                                )
                            else:
                                wanted_file.set_data(None, None, True)

                        keys_to_remove.append(key)
                        asyncio.create_task(terrain_request.process())

                for key in keys_to_remove:
                    del self.terrain_requests[key]

                # try to free memory by resizing the underlying map
                self.terrain_requests = dict(self.terrain_requests.items())

            except Exception as e:
                logging.error(f"Error processing terrain request: {e}")

    async def _cleanup(self):
        """Check the cache for expired items and remove them"""

        async with self.lock:
            keep = []
            for _, terrain_request in list(self.terrain_requests.items()):
                for wanted_file in terrain_request.wanted_files:
                    keep.append(wanted_file.key)

            self.cache.clear_expired(keep)
            if len(self.terrain_requests) == 0:
                self.terrain_requests = {}
                self._try_reset_executor()

            if len(self.open_requests) == 0:
                self.open_requests = set()

            if self.processing_queue.qsize() == 0:
                self.processing_queue = asyncio.Queue()

            if logging.getLogger().level == logging.DEBUG:
                self._print_debug_info()

    def _get_executor(self):
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=40)

        return self.executor

    def _try_reset_executor(self):
        # If the executor is not doing anything, shut it down
        if self.executor and self.executor._work_queue.empty():
            self.executor.shutdown(wait=False)
            self.executor = None

    def _print_debug_info(self):
        memory_info = psutil.Process(self.pid).memory_info()
        memory_usage_mb = memory_info.rss / (1024 * 1024)
        logging.debug(f"Memory usage: {memory_usage_mb} MB")
        logging.debug(
            f"Factory: terrain reqs: {len(self.terrain_requests)}, cache size: {len(self.cache_test)}, open requests: {len(self.open_requests)}, queue size: {self.processing_queue.qsize()}"
        )
