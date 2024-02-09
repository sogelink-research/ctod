import asyncio
import logging
import time

from ctod.core.cog.cog_request import CogRequest
from ctod.core.terrain.terrain_request import TerrainRequest


class TerrainFactory:
    """Factory to handle TerrainRequests
    
    TerrainFactory has an in memory cache for COG data and a processing queue to prevent
    duplicate requests being send to the COG, this is important when we need adjecent tiles
    for the terrain generation.
    
    TerrainFactory checks if TerrainRequest are ready for precessing and if so, processes them.
    """
    
    def __init__(self, cache_expiry_seconds=60):
        self.cache_expiry_seconds = cache_expiry_seconds
        self.cache = {}
        self.open_requests = set()
        self.terrain_requests = {}
        self.processing_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
            
    async def handle_request(self, terrain_request: TerrainRequest) -> asyncio.Future:
        """Handle a TerrainRequest

        Args:
            terrain_request (TerrainRequest): Terrain requested trough API

        Returns:
            asyncio.Future: Future which will be set when the terrain is ready
        """

        terrain_request.register_cancel_callback(self._handle_cancelled_request)
        
        if not terrain_request.cancelled:
            async with self.lock:
                # add terrain_request to terrain_requests cache
                self.terrain_requests[terrain_request.key] = terrain_request
                
                # loop over wanted files and add to processing queue if needed
                for wanted_file in terrain_request.wanted_files:
                    # Check if the data is already available in the cache
                    if wanted_file.key not in self.cache:
                        if wanted_file.key not in [item[0].key for item in self.processing_queue._queue] and wanted_file.key not in self.open_requests:
                            # Add a new request to the processing queue which handles the download of the cog data
                            cog_request = CogRequest(wanted_file.tms, wanted_file.cog, wanted_file.z, wanted_file.x, wanted_file.y, wanted_file.cog_processor, wanted_file.cog_reader_pool, wanted_file.resampling_method, wanted_file.generate_normals)
                            await self.processing_queue.put((cog_request,))
                          
                    
                    # If the data is already available, set it in the wanted file
                    else:
                        wanted_file.set_data(self.cache[wanted_file.key].data, self.cache[wanted_file.key].processed_data, self.cache[wanted_file.key].is_out_of_bounds)

        await self._process_queue() 
        await self._process_terrain_requests()
        
        return await terrain_request.wait()
            
    async def start_periodic_check(self, interval:int=5):
        """Periodically check the cache for expired items

        Args:
            interval (int, optional): The amount of second between checks. Defaults to 5.
        """
        
        while True:
            await asyncio.sleep(interval)
            await self._check_cache_expiry()
            
    async def _process_queue(self):
        """Process the queue with CogRequests"""

        async with self.lock:
            while not self.processing_queue.empty():            
                cog_request, = await self.processing_queue.get()
                self.open_requests.add(cog_request.key)
                future = cog_request.download_tile_async()
                asyncio.ensure_future(self._process_completed_cog_request(cog_request, future))

    async def _process_completed_cog_request(self, cog_request, future):
        await future  # Wait for the completion of the future

        # Process the completed request
        async with self.lock:
            if cog_request:
                self.open_requests.remove(cog_request.key)
                self.cache[cog_request.key] = cog_request

                for _, terrain_request in list(self.terrain_requests.items()):
                    for wanted_file in terrain_request.wanted_files:
                        if wanted_file.key == cog_request.key:
                            wanted_file.set_data(cog_request.data, cog_request.processed_data, cog_request.is_out_of_bounds)

        await self._process_terrain_requests()
        
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
                if wanted_file[0].key not in [wanted_file.key for terrain_request in self.terrain_requests.values() for wanted_file in terrain_request.wanted_files]:
                    self.processing_queue._queue.remove(wanted_file)
                if wanted_file[0].key in self.open_requests:
                    self.open_requests.remove(wanted_file[0].key)
                    
    async def _process_terrain_requests(self):
        """Check and run process on terrain requests when ready for processing"""
        
        async with self.lock:
            keys_to_remove = []
            
            for key, terrain_request in list(self.terrain_requests.items()):                
                if terrain_request.has_all_data() and not terrain_request.result_set:
                    terrain_request.process()
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:                
                del self.terrain_requests[key]
        
    async def _check_cache_expiry(self):
        """Check the cache for expired items and remove them"""
        
        async with self.lock:
            current_time = time.time()

            keys_to_remove = [
                key
                for key, cog_request in list(self.cache.items())
                if current_time - cog_request.timestamp > self.cache_expiry_seconds                
            ]
            
            # do not remove if key is in a terrain_request wanted file
            for key, terrain_request in list(self.terrain_requests.items()):
                for wanted_file in terrain_request.wanted_files:
                    if wanted_file.key in keys_to_remove:
                        keys_to_remove.remove(wanted_file.key)

            for key in keys_to_remove:
                del self.cache[key]
            
        
        logging.debug(f"Factory: terrain reqs: {len(self.terrain_requests)}, cache size: {len(self.cache)}, open requests: {len(self.open_requests)}, queue size: {self.processing_queue.qsize()}")