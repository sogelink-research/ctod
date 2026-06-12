"""Unexpected-failure path: transient errors fail retriably, never cached.

A generic download error (e.g. S3/GDAL) must NOT be cached as empty terrain —
that would persist into the durable .terrain cache and serve flat ground over
real data with a 200. Instead the factory fails the dependent terrain
request(s) directly (retriable 5xx) and leaves nothing stranded, so a later
request for the same key is not poisoned.
"""

import pytest

from .conftest import FakeCogRequest, make_terrain_request, settle


async def test_transient_failure_fails_request_without_caching(factory):
    key = "cog-key"
    terrain_request = make_terrain_request("terrain-key", [key])
    factory.terrain_requests[terrain_request.key] = terrain_request
    factory.open_requests.add(key)

    boom = RuntimeError("transient S3 read failure")
    cog_request = FakeCogRequest(key, error=boom)
    await factory._process_cog_request(cog_request)

    # The waiter resolves as a failure (becomes a retriable 5xx at the handler).
    with pytest.raises(RuntimeError, match="transient S3 read failure"):
        await terrain_request.wait()

    # Nothing was cached: a transient error never becomes persistent flat ground.
    assert key not in factory.cache.keys
    cached = await factory.cache.get([key])
    assert cached == {}

    # No stranded state.
    assert factory.open_requests == set()
    assert factory.terrain_requests == {}


async def test_same_key_not_poisoned_after_failure(factory):
    """A subsequent request for the same key resolves instead of hanging."""

    key = "cog-key"
    first = make_terrain_request("terrain-1", [key])
    factory.terrain_requests[first.key] = first
    factory.open_requests.add(key)

    await factory._process_cog_request(FakeCogRequest(key, error=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        await first.wait()

    # The key is neither cached nor open, so handle_request would re-queue it.
    assert key not in factory.cache.keys
    assert key not in factory.open_requests

    # Simulate that re-queued request succeeding this time.
    second = make_terrain_request("terrain-2", [key])
    factory.terrain_requests[second.key] = second
    factory.open_requests.add(key)

    await factory._process_cog_request(FakeCogRequest(key))  # no error

    result = await second.wait()
    assert result == b"TILE"
    await settle(lambda: not factory.open_requests and not factory.terrain_requests)
    assert factory.open_requests == set()
    assert factory.terrain_requests == {}


async def test_cancelled_waiter_does_not_strand_others(factory):
    """A waiter cancelled mid-flight (client disconnect) must not abort the fail loop.

    Its future is `done()` with `result_set` still False, so a naive
    `set_exception` would raise InvalidStateError and strand the *other* waiters
    that were already popped from terrain_requests.
    """

    key = "cog-key"
    first = make_terrain_request("terrain-1", [key])
    second = make_terrain_request("terrain-2", [key])
    factory.terrain_requests[first.key] = first
    factory.terrain_requests[second.key] = second
    factory.open_requests.add(key)

    # Simulate the client of the first request disconnecting.
    first.future.cancel()

    await factory._process_cog_request(FakeCogRequest(key, error=RuntimeError("boom")))

    # The cancelled waiter is left as-is (no crash, no overwrite)...
    assert first.future.cancelled()
    # ...and the second waiter is still failed rather than stranded.
    with pytest.raises(RuntimeError, match="boom"):
        await second.wait()

    assert factory.open_requests == set()
    assert factory.terrain_requests == {}
