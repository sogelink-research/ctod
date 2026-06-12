"""Reader-symmetry test for CogRequest.download_tile_async.

Under a failure storm a transient download error must not leak readers from the
pool. The acquired reader is returned in a `finally`, so it goes back whether the
executor download succeeds or throws.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from ctod.core.cog.cog_request import CogRequest


class _BoomError(Exception):
    pass


class _FakeReader:
    def __init__(self, error=None):
        self._error = error
        self.returned = False

    def download_tile(self, x, y, z, loop, no_data, resampling_method, **kwargs):
        if self._error:
            raise self._error
        return None  # treated as out-of-bounds by _download

    def return_reader(self):
        self.returned = True


class _FakePool:
    def __init__(self, reader):
        self.reader = reader

    async def get_reader(self, cog, tms):
        return self.reader


class _FakeProcessor:
    def get_reader_kwargs(self):
        return {}


def _make_request(reader):
    """A CogRequest wired to fakes, bypassing the tms/key-building __init__."""

    request = CogRequest.__new__(CogRequest)
    request.tms = None
    request.cog = "/vsis3/bucket/dsm.tif"
    request.x, request.y, request.z = 1, 2, 3
    request.no_data = 0
    request.resampling_method = None
    request.cog_processor = _FakeProcessor()
    request.cog_reader_pool = _FakePool(reader)
    request.data = None
    request.processed_data = None
    request.is_out_of_bounds = False
    return request


async def test_reader_returned_when_download_raises():
    reader = _FakeReader(error=_BoomError("S3 read failed"))
    request = _make_request(reader)

    with pytest.raises(_BoomError):
        await request.download_tile_async(ThreadPoolExecutor(max_workers=1))

    assert reader.returned is True


async def test_reader_returned_on_success():
    reader = _FakeReader()
    request = _make_request(reader)

    await request.download_tile_async(ThreadPoolExecutor(max_workers=1))

    assert reader.returned is True
    # download_tile returned None -> out of bounds, nothing downloaded.
    assert request.is_out_of_bounds is True
