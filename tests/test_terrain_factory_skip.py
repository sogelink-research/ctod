"""Deterministic-skip path: a no-overview DSM is cached as out-of-bounds.

A NoOverviewsError from the download is a raster-wide skip. The factory caches
`{data: None, processed_data: None, is_out_of_bounds: True}`, which flows through
the normal cache_changed path: the waiter resolves with an (empty) tile,
open_requests is cleared, and nothing is left stranded.
"""

from ctod.core.cog.reader.cog_reader import NoOverviewsError

from .conftest import FakeCogRequest, make_terrain_request, settle


async def test_no_overview_skip_resolves_waiter_as_empty(factory):
    key = "cog-key"
    terrain_request = make_terrain_request("terrain-key", [key])
    factory.terrain_requests[terrain_request.key] = terrain_request
    factory.open_requests.add(key)

    cog_request = FakeCogRequest(key, error=NoOverviewsError("no overviews"))
    await factory._process_cog_request(cog_request)

    # Waiter resolves with the generator's (empty) tile rather than hanging.
    result = await terrain_request.wait()
    assert result == b"TILE"

    # The skip was cached as out-of-bounds with null data...
    cached = await factory.cache.get([key])
    assert cached[key] == {
        "data": None,
        "processed_data": None,
        "is_out_of_bounds": True,
    }
    # ...and the wanted file was populated from that cache entry.
    assert terrain_request.wanted_files[0].is_out_of_bounds is True

    # No stranded state: nothing left in open_requests or terrain_requests.
    await settle(lambda: not factory.open_requests and not factory.terrain_requests)
    assert factory.open_requests == set()
    assert factory.terrain_requests == {}
