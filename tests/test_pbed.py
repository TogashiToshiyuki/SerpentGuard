"""Tests for the verified, incremental PBED subset and slice mathematics."""

from __future__ import annotations

import io
import logging
import math
from pathlib import Path

import pytest

from serpentguard.pbed import PbedReadPolicy, parse_pbed_binary
from serpentguard.pbed_plot import (
    create_pbed_slice_figure,
    project_pbed_centers,
    slice_pbed_placements,
)

FIXTURES = Path("tests/fixtures/pbed")


def test_valid_five_field_pbed_records_and_bounding_box() -> None:
    path = FIXTURES / "valid" / "placements.dat"
    with path.open("rb") as stream:
        result = parse_pbed_binary(
            stream,
            source_name="placements.dat",
            size_bytes=path.stat().st_size,
        )

    assert not result.diagnostics
    assert result.data is not None
    assert result.data.valid_record_count == 3
    assert result.data.invalid_record_count == 0
    assert result.data.placements[1].universe == "pebble_b"
    assert result.data.bounding_box is not None
    assert result.data.bounding_box.model_dump() == {
        "xmin": -2.25,
        "xmax": 3.5,
        "ymin": -1.0,
        "ymax": 1.25,
        "zmin": -1.25,
        "zmax": 1.5,
    }


def test_malformed_nonfinite_and_nonpositive_records_are_excluded() -> None:
    content = (FIXTURES / "malformed" / "malformed.dat").read_bytes()
    result = parse_pbed_binary(
        io.BytesIO(content),
        source_name="malformed.dat",
        size_bytes=len(content),
    )

    assert result.data is not None
    assert result.data.total_record_count == 4
    assert result.data.valid_record_count == 1
    assert result.data.invalid_record_count == 3
    assert [item.code for item in result.diagnostics] == [
        "PBED_COLUMN_COUNT",
        "PBED_NUMERIC_VALUE",
        "PBED_NON_POSITIVE_RADIUS",
    ]
    assert [item.record_number for item in result.diagnostics] == [2, 3, 4]


def test_size_record_encoding_and_empty_limits() -> None:
    oversized = parse_pbed_binary(
        io.BytesIO(b"0 0 0 1 u\n"),
        source_name="large.dat",
        size_bytes=20,
        policy=PbedReadPolicy(max_file_size_bytes=10, max_record_count=10),
    )
    assert oversized.data is None
    assert oversized.diagnostics[0].code == "PBED_FILE_SIZE_LIMIT"

    streamed_oversized = parse_pbed_binary(
        io.BytesIO(b"0 0 0 1 universe\n"),
        source_name="growing.dat",
        size_bytes=1,
        policy=PbedReadPolicy(max_file_size_bytes=10, max_record_count=10),
    )
    assert streamed_oversized.data is not None
    assert streamed_oversized.data.truncated
    assert streamed_oversized.diagnostics[0].code == "PBED_FILE_SIZE_LIMIT"

    records = b"".join(b"0 0 0 1 u\n" for _ in range(4))
    limited = parse_pbed_binary(
        io.BytesIO(records),
        source_name="records.dat",
        size_bytes=len(records),
        policy=PbedReadPolicy(max_file_size_bytes=1000, max_record_count=3),
    )
    assert limited.data is not None
    assert limited.data.valid_record_count == 3
    assert limited.data.truncated
    assert limited.diagnostics[0].code == "PBED_RECORD_LIMIT"

    invalid_encoding = parse_pbed_binary(
        io.BytesIO(b"0 0 0 1 u\n\xff\n"),
        source_name="encoding.dat",
        size_bytes=14,
    )
    assert invalid_encoding.data is not None
    assert invalid_encoding.data.truncated
    assert invalid_encoding.diagnostics[-1].code == "PBED_ENCODING"
    assert invalid_encoding.diagnostics[-1].line == 2

    empty = parse_pbed_binary(
        io.BytesIO(b"\n  \n"),
        source_name="empty.dat",
        size_bytes=4,
    )
    assert empty.data is not None
    assert empty.data.total_record_count == 2
    assert empty.data.invalid_record_count == 2
    assert [item.code for item in empty.diagnostics] == [
        "PBED_BLANK_LINE",
        "PBED_BLANK_LINE",
        "PBED_EMPTY",
    ]


def test_large_reader_iterates_lines_without_full_stream_read() -> None:
    class LineOnlyStream:
        def __init__(self, line_count: int) -> None:
            self.remaining = line_count

        def __iter__(self) -> LineOnlyStream:
            return self

        def __next__(self) -> bytes:
            if self.remaining == 0:
                raise StopIteration
            self.remaining -= 1
            return b"0 0 0 1 u\n"

        def read(self, *_args: object) -> bytes:
            raise AssertionError("full-file read is not permitted")

    stream = LineOnlyStream(2_000)
    result = parse_pbed_binary(  # type: ignore[arg-type]
        stream,
        source_name="generated.dat",
        size_bytes=24_000,
        policy=PbedReadPolicy(max_file_size_bytes=30_000, max_record_count=2_001),
    )

    assert result.data is not None
    assert result.data.valid_record_count == 2_000


def test_raw_malformed_content_is_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    secret_record = b"sensitive-coordinate-token 2 3 4 universe\n"
    with caplog.at_level(logging.DEBUG):
        result = parse_pbed_binary(
            io.BytesIO(secret_record),
            source_name="private.dat",
            size_bytes=len(secret_record),
        )

    assert result.diagnostics
    assert "sensitive-coordinate-token" not in caplog.text
    assert "sensitive-coordinate-token" not in repr(result)


def test_pbed_xy_slice_uses_exact_sphere_cross_section() -> None:
    content = b"1 2 3 5 sphere\n0 0 -10 1 absent\n"
    parsed = parse_pbed_binary(
        io.BytesIO(content),
        source_name="slice.dat",
        size_bytes=len(content),
    )
    assert parsed.data is not None

    sliced = slice_pbed_placements(parsed.data, z=6.0)

    assert sliced.total_placement_count == 2
    assert sliced.intersecting_placement_count == 1
    assert sliced.circles[0].x == 1
    assert sliced.circles[0].y == 2
    assert sliced.circles[0].radius == pytest.approx(4.0)
    assert math.isfinite(sliced.circles[0].radius)
    figure = create_pbed_slice_figure(sliced, title="Synthetic PBED slice")
    assert figure.axes[0].get_title() == "Synthetic PBED slice"


def test_pbed_slice_rejects_nonfinite_z() -> None:
    parsed = parse_pbed_binary(
        io.BytesIO(b"0 0 0 1 u\n"),
        source_name="slice.dat",
        size_bytes=12,
    )
    assert parsed.data is not None
    with pytest.raises(ValueError, match="must be finite"):
        slice_pbed_placements(parsed.data, z=math.inf)


def test_pbed_projection_is_distinct_from_exact_z_slice_and_grouped_by_universe() -> (
    None
):
    content = b"1 2 3 5 fuel\n0 0 -10 1 moderator\n"
    parsed = parse_pbed_binary(
        io.BytesIO(content), source_name="projection.dat", size_bytes=len(content)
    )
    assert parsed.data is not None
    projection = project_pbed_centers(parsed.data)
    sliced = slice_pbed_placements(parsed.data, z=6.0)

    assert projection.mode == "projection"
    assert len(projection.circles) == 2
    assert len(sliced.circles) == 1
    assert projection.circles[0].radius == 5
    figure = create_pbed_slice_figure(projection, title="XY center projection")
    assert len(figure.axes[0].collections) == 2
    assert len(figure.axes[0].get_legend().get_texts()) == 2
