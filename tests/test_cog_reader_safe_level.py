"""Regression test for the no-overview crash.

`_set_safe_level` used to do `max(self.rio_reader.dataset.overviews(1))`. A DSM
shipped without overviews returns `[]`, so `max([])` raised a bare
`ValueError: max() arg is an empty sequence` deep inside `CogReader.__init__`.
The fix raises a typed `NoOverviewsError` instead, which the factory recognises
as a deterministic, raster-wide skip.
"""

import morecantile
import pytest

from ctod.core.cog.reader.cog_reader import CogReader, NoOverviewsError

TMS = morecantile.tms.get("WebMercatorQuad")


class _FakeBounds:
    left = 0.0
    right = 1.0


class _FakeInfo:
    bounds = _FakeBounds()


class _FakeDataset:
    def __init__(self, overviews, width=10000):
        self.width = width
        self._overviews = overviews

    def overviews(self, band):
        return self._overviews


class _FakeRioReader:
    def __init__(self, overviews):
        self.dataset = _FakeDataset(overviews)

    def info(self):
        return _FakeInfo()


def _make_reader(overviews):
    """A CogReader with a stubbed rio reader, bypassing the GDAL-backed __init__."""

    reader = CogReader.__new__(CogReader)
    reader.cog = "/vsis3/bucket/no-overviews-dsm.tif"
    reader.tms = TMS
    reader.unsafe = False
    reader.rio_reader = _FakeRioReader(overviews)
    return reader


def test_no_overviews_raises_typed_error():
    reader = _make_reader([])

    with pytest.raises(NoOverviewsError) as excinfo:
        reader._set_safe_level()

    # The message names the offending raster so the skip log is actionable.
    assert reader.cog in str(excinfo.value)


def test_with_overviews_sets_a_safe_level():
    reader = _make_reader([2, 4, 8, 16])

    reader._set_safe_level()

    assert isinstance(reader.safe_level, int)
    assert reader.safe_level >= 0
