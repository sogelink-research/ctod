"""Shared fakes and fixtures for the TerrainFactory tests.

The factory's machinery resolves a terrain request's waiter via *cache presence*
(`cache.add` -> `cache_updated` -> `cache_changed` -> `process()`). These fakes
present exactly the interface the factory touches, so the tests exercise the
real factory control flow without GDAL, S3, or the quantized-mesh generators.
"""

import asyncio

import pytest_asyncio

from ctod.core.factory.terrain_factory import TerrainFactory
from ctod.core.terrain.terrain_request import TerrainRequest


class FakeWantedFile:
    """Stand-in for a CogRequest inside a TerrainRequest's wanted_files."""

    def __init__(self, key):
        self.key = key
        self.data = None
        self.processed_data = None
        self.is_out_of_bounds = False

    def set_data(self, data, processed_data, is_out_of_bounds):
        self.data = data
        self.processed_data = processed_data
        self.is_out_of_bounds = is_out_of_bounds


class FakeCogRequest:
    """A CogRequest whose download either succeeds or raises a chosen error."""

    def __init__(self, key, cog="/vsis3/bucket/dsm.tif", z=10, x=1, y=2, error=None):
        self.key = key
        self.cog = cog
        self.z, self.x, self.y = z, x, y
        self.data = None
        self.processed_data = None
        self.is_out_of_bounds = False
        self._error = error

    async def download_tile_async(self, executor):
        if self._error is not None:
            raise self._error
        self.data = object()
        self.processed_data = object()


class FakeTerrainGenerator:
    def __init__(self, result=b"TILE"):
        self.result = result

    def generate(self, terrain_request):
        return self.result


def make_terrain_request(key, wanted_keys, generator_result=b"TILE"):
    """A real TerrainRequest with a fake generator, bypassing the heavy __init__."""

    request = TerrainRequest.__new__(TerrainRequest)
    request.wanted_files = [FakeWantedFile(k) for k in wanted_keys]
    request.wanted_file_keys = list(wanted_keys)
    request.key = key
    request.processing = False
    request.result_set = False
    request.future = asyncio.Future()
    request.terrain_generator = FakeTerrainGenerator(generator_result)
    return request


async def settle(predicate, *, timeout=2.0):
    """Yield to the loop until `predicate()` is true (factory work is task-based)."""

    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError("condition not reached before timeout")
        await asyncio.sleep(0)


@pytest_asyncio.fixture
async def factory(tmp_path):
    factory = TerrainFactory(str(tmp_path), "test_cache.db", cache_ttl=30)
    await factory.cache.initialize()
    yield factory
    factory.cache.close()
