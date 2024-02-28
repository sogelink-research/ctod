import asyncio
import time
import pickle
import os
import time
import logging

from typing import Any, Callable, Dict, List
from pyee import AsyncIOEventEmitter
import aiosqlite


class FactoryCache:
    """A simple SQLite cache to store and retrieve cog raw and processed data.

    When doing everything in memory the memory can grow fast and often results in memory
    not directly released back to the OS. To keep a low memory footprint we use a SQLite database
    for a file based approach.

    In a later stage we can add the option for Redis aiocache cache to share state between
    multiple servers if needed.

    The cache can be shared between workers to take full advantage of the available resources
    instead of running only a single worker.
    """

    def __init__(self, cache_path: str, db_name: str = "factory_cache.db", in_memory: bool = False, ttl: int = 30):
        """
        Initialize the FactoryCache object.

        Args:
            cache_path (str): The path to the cache database file.
            db_name (str, optional): The name of the cache database file. Defaults to "factory_cache.db".
            in_memory (bool, optional): Whether to use an in-memory database. Defaults to False.
            ttl (int, optional): The time-to-live (in seconds) for cached items. Defaults to 60.
            pool_size (int, optional): The size of the connection pool. Defaults to 5.
        """

        self.ttl = ttl
        self.db_name = (
            f"{cache_path}/{db_name}"
            if cache_path is not None and not in_memory
            else db_name if not in_memory else ":memory:"
        )
        self.ee = AsyncIOEventEmitter()
        self.keys = []
        self.batch = {}
        self.batch_processing = False
        self.batch_rerun = False
        self.lock = asyncio.Lock()

    async def initialize(self):
        await self._create_table()

    async def _create_table(self):
        """
        Create the cache table if it does not exist.
        """
        
        async with aiosqlite.connect(self.db_name) as db:
            try:
                await db.execute(
                    "CREATE TABLE IF NOT EXISTS cache (key TEXT, value BLOB, timestamp REAL)"
                )
                await db.commit()
            except aiosqlite.Error as e:
                logging.error(f"Error creating factory cache table: {e}")

    async def update_keys(self) -> None:
        """
        Update the list of keys in the cache.
        """
        
        async with self.lock:
            self.keys = await self._get_keys()

    async def add(self, key: str, value: Any) -> None:
        """
        Add a key-value pair to the cache.
        
        Add will trigger many times and very fast, to increase performance we process
        the items batched. Items will be saved up when a batch is being processed, the
        saved up batch will be processed when the previous batch is done.

        Args:
            key (str): The key to identify the value.
            value (Any): The value to be stored in the cache.
        """
        
        async with self.lock:
            self.batch[key] = value

        if self.batch_processing:
            self.batch_rerun = True
        else:
            self.batch_processing = True
            asyncio.create_task(self._add_batched())

    async def _add_batched(self) -> None:
        """
        Process the batched items and add them to the cache.

        This method is called asynchronously to process the batched items and add them to the cache.
        """
        async with self.lock:
            batch_copy = self.batch.copy()
            self.batch.clear()

        if batch_copy:
            try:
                async with aiosqlite.connect(self.db_name) as db:
                    for key, value in batch_copy.items():
                        await db.execute(
                            """
                            INSERT OR REPLACE INTO cache (key, value, timestamp) 
                            VALUES (?, ?, ?)
                            """,
                            (key, pickle.dumps(value), time.time()),
                        )
                    await db.commit()
            except aiosqlite.Error as e:
                logging.error(f"Error adding to factory cache: {e}")

            await self.update_keys()
            
            new_keys = set(batch_copy.keys())
            self.ee.emit("cache_updated", new_keys)

        # If add was called while processing the batch, pickup the new batch
        if self.batch_rerun:
            self.batch_rerun = False
            await self._add_batched()
        else:
            self.batch_processing = False

    async def get(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get the values associated with the specified keys from the cache.

        Args:
            keys (List[str]): The keys to retrieve the values for.

        Returns:
            Dict[str, Any]: A dictionary where the keys are the keys passed to the function and the values are the corresponding values from the cache.
        """

        placeholders = ", ".join("?" for _ in keys)
        query = f"SELECT * FROM cache WHERE key IN ({placeholders})"

        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(query, keys)
                entries = await cursor.fetchall()

                if entries is None:
                    return {key: None for key in keys}

                values = {entry[0]: pickle.loads(entry[1]) for entry in entries}
                return values

        except aiosqlite.Error as e:
            logging.error(f"Error getting from factory cache: {e}")

    async def clear_expired(self, keys_to_keep: List[str]) -> None:
        try:
            async with aiosqlite.connect(self.db_name) as db:
                placeholders = ', '.join('?' for _ in keys_to_keep)
                query = f"DELETE FROM cache WHERE (strftime('%s', 'now') - timestamp) > ? AND key NOT IN ({placeholders})"
                await db.execute(query, (self.ttl, *keys_to_keep))
                await db.commit()
                
        except aiosqlite.Error as e:
            logging.error(f"Error clearing expired items from factory cache: {e}")
            
        finally:
            await self.update_keys()

    async def get_cache_size(self) -> int:
        """
        Get the size of the cache.

        Returns:
            int: The number of items in the cache.
        """
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM cache")
                count = await cursor.fetchone()
                return count[0]
        except aiosqlite.Error as e:
            logging.error(f"Error getting cache size: {e}")
        
        return None

    def on_cache_change(self, func: Callable[[str, Any], None]) -> None:
        """
        Register a callback function to be called when new data is added to the cache.

        Args:
            func (Callable[[str, Any], None]): The callback function to be registered.
                It should take two arguments: the key (str) and the value (Any) that are set in the cache.
                The function should not return anything.

        Returns:
            None
        """

        self.ee.on("cache_updated", func)
        
    async def _get_keys(self) -> List[str]:
        """
        Get all keys stored in the cache.

        Returns:
            List[str]: A list of keys stored in the cache.
        """

        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute("SELECT key FROM cache")
                keys = [row[0] for row in await cursor.fetchall()]
                return keys
        except aiosqlite.Error as e:
            print("ERROR GET KEY", e)

    async def _clear_cache(self) -> None:
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute("DELETE FROM cache")
                await db.commit()
                
        except aiosqlite.Error as e:
            logging.error(f"Error clearing factory cache: {e}")
            
        finally:
            await self.update_keys()

    def close(self) -> None:
        """
        Close the FactoryCache instance.

        This function removes all event listeners and deletes the database file if it is not an in-memory database.

        Returns:
            None
        """

        self.ee.remove_all_listeners()

        if self.db_name != ":memory:" and os.path.exists(self.db_name):
            os.remove(self.db_name)

    def __del__(self):
        self.close()
