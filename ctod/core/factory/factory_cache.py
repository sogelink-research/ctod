import sqlite3
import time
import pickle
import os
from typing import Any, Callable, List, Optional
from pyee import AsyncIOEventEmitter


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
    
    def __init__(self, in_memory: bool = False, ttl: int = 60):
        """
        Initialize the FactoryCache object.

        Args:
            db_name (str, optional): The name of the SQLite database file. Defaults to ":memory:".
            ttl (int, optional): The time-to-live (in seconds) for cached items. Defaults to 60.
        """
        
        self.ttl = ttl
        self.db_name = "factory_cache.db" if not in_memory else ":memory:"
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self._create_table()
        self._clear()
        self.ee = AsyncIOEventEmitter()
        self.keys = []

    def _create_table(self) -> None:
        """
        Create the cache table if it doesn't exist.
        """
        
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB,
                timestamp REAL
            )
        """
        )
        self.conn.commit()

    async def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache with the specified key.

        Args:
            key (str): The key to associate with the value.
            value (Any): The value to be stored in the cache.
        """
        
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, timestamp) 
            VALUES (?, ?, ?)
        """,
            (key, pickle.dumps(value), time.time()),
        )
        self.conn.commit()
        self.keys = self.get_keys()
        self.ee.emit("set", key)

    def get(self, key: str) -> Any:
        """
        Get the value associated with the specified key from the cache.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            Any: The value associated with the key, or None if the key does not exist or has expired.
        """
        
        self.cursor.execute(
            """
            SELECT value FROM cache WHERE key = ?
        """,
            (key,),
        )
        result = self.cursor.fetchone()
        if result is None:
            return None

        return pickle.loads(result[0])

    def delete(self, key: str) -> None:
        """
        Delete the value associated with the specified key from the cache.

        Args:
            key (str): The key to delete from the cache.
        """
        
        self.cursor.execute(
            """
            DELETE FROM cache WHERE key = ?
        """,
            (key,),
        )
        self.conn.commit()
        self.keys = self.get_keys()

    def _clear(self) -> None:
        """
        Clear the entire cache by deleting all entries.

        This function deletes all entries from the cache table in the SQLite database.
        """
        
        self.cursor.execute("DELETE FROM cache")
        self.conn.commit()
        self.keys = self.get_keys()

    def clear_expired(self, keys_to_keep: Optional[List[str]] = None) -> None:
        """
        Clear expired entries from the cache.

        This function deletes all entries from the cache table in the SQLite database
        where the difference between the current timestamp and the stored timestamp is greater than the TTL,
        excluding the keys provided in keys_to_keep.

        Note: The TTL (Time To Live) is the maximum time in seconds that an entry can remain in the cache.

        Args:
            keys_to_keep (Optional[List[str]]): A list of keys to keep in the cache.

        Returns:
            None
        """
        
        keys_to_keep = keys_to_keep or []
        placeholders = ', '.join('?' for _ in keys_to_keep)
        query = f"""
            DELETE FROM cache WHERE (? - timestamp) > ? AND key NOT IN ({placeholders})
        """
        self.cursor.execute(
            query,
            (time.time(), self.ttl, *keys_to_keep),
        )
        self.conn.commit()
        self.keys = self.get_keys()

    def get_keys(self) -> List[str]:
        """
        Get all keys stored in the cache.

        Returns:
            List[str]: A list of keys stored in the cache.
        """
        
        self.cursor.execute("SELECT key FROM cache")
        return [row[0] for row in self.cursor.fetchall()]

    def on_set(self, func: Callable[[str, Any], None]) -> None:
        """
        Register a callback function to be called when a key-value pair is set in the cache.

        Args:
            func (Callable[[str, Any], None]): The callback function to be registered.
                It should take two arguments: the key (str) and the value (Any) that are set in the cache.
                The function should not return anything.

        Returns:
            None
        """
        
        self.ee.on("set", func)

    def close(self) -> None:
        """
        Close the FactoryCache instance.

        This function removes all event listeners, closes the SQLite connection,
        and deletes the database file if it is not an in-memory database.

        Returns:
            None
        """
        
        self.ee.remove_all_listeners()
        self.conn.close()
        
        if self.db_name != ":memory:":
            os.remove(self.db_name)
    
    def __del__(self):
        self.conn.close()