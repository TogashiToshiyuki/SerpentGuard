"""Tests for uploaded-bundle and authorized-root PBED resolution."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from serpentguard.pbed import PbedReadPolicy
from serpentguard.references import (
    ABSOLUTE_TARGET_MARKER,
    INVALID_TARGET_MARKER,
    ExternalResolutionReport,
    LocalProjectSource,
    ReferencePolicyError,
    ReferenceResolutionPolicy,
    UploadedSourceBundle,
    extract_pbed_references,
    normalize_bundle_name,
)

FIXTURES = Path("tests/fixtures/pbed")


def _uploaded_fixture(case: str) -> UploadedSourceBundle:
    directory = FIXTURES / case
    main = (directory / "main.inp").read_bytes()
    supporting = [
        (path.name, path.read_bytes())
        for path in directory.iterdir()
        if path.name != "main.inp" and path.is_file()
    ]
    return UploadedSourceBundle(
        main_name="main.inp",
        main_content=main,
        supporting_files=supporting,
    )


def test_verified_pbed_card_extraction() -> None:
    references, diagnostics = extract_pbed_references(
        'pbed bed background "folder/data file.dat" pow\n',
        source_name="case/main.inp",
    )

    assert not diagnostics
    assert references[0].model_dump() == {
        "source_name": "case/main.inp",
        "source_line": 1,
        "reference_type": "pbed",
        "target_name": "case/folder/data file.dat",
        "path_kind": "relative",
        "universe": "bed",
        "background_universe": "background",
        "power_output_requested": True,
    }


def test_uploaded_bundle_resolves_and_identifies_unused_support() -> None:
    directory = FIXTURES / "valid"
    bundle = UploadedSourceBundle(
        main_name="main.inp",
        main_content=(directory / "main.inp").read_bytes(),
        supporting_files=[
            ("placements.dat", (directory / "placements.dat").read_bytes()),
            ("unused.dat", b"0 0 0 1 unused\n"),
        ],
    )

    report = bundle.resolve_pbed()

    assert report.mode == "uploaded_bundle"
    assert report.references[0].status == "resolved"
    assert report.references[0].record_count == 3
    assert report.references[0].pbed_data is not None
    assert report.unused_supporting_files == ("unused.dat",)


def test_windows_mixed_separator_casefold_and_unicode_names() -> None:
    assert normalize_bundle_name(r"folder\.\日本語\data.dat") == (
        "folder/日本語/data.dat"
    )
    bundle = UploadedSourceBundle(
        main_name=r"case\main.inp",
        main_content='pbed bed bg "DATA\\配置.DAT"\n'.encode(),
        supporting_files=[("case/data/配置.dat", b"0 0 0 1 u\n")],
    )

    report = bundle.resolve_pbed()

    assert report.references[0].status == "resolved"
    assert report.references[0].reference.target_name == "case/DATA/配置.DAT"

    spaced = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "data file.dat"\n',
        supporting_files=[("data file.dat", b"0 0 0 1 u\n")],
    ).resolve_pbed()
    assert spaced.references[0].status == "resolved"


@pytest.mark.parametrize("name", ["bad:name.dat", "NUL.dat", "trailing. "])
def test_windows_invalid_bundle_components_are_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="Windows-invalid"):
        normalize_bundle_name(name)


@pytest.mark.parametrize(
    ("case", "status", "marker"),
    [
        ("missing", "missing", "missing.dat"),
        ("traversal", "rejected", INVALID_TARGET_MARKER),
        ("absolute", "rejected", ABSOLUTE_TARGET_MARKER),
    ],
)
def test_missing_traversal_and_absolute_references(
    case: str,
    status: str,
    marker: str,
) -> None:
    report = _uploaded_fixture(case).resolve_pbed()

    assert report.references[0].status == status
    assert report.references[0].reference.target_name == marker


def test_absolute_reference_is_redacted_from_normalized_report() -> None:
    report = _uploaded_fixture("absolute").resolve_pbed()
    serialized = json.dumps(report.model_dump(mode="json"))

    assert r"C:\synthetic-private" not in serialized
    assert ABSOLUTE_TARGET_MARKER in serialized


def test_duplicate_supporting_names_are_ambiguous() -> None:
    bundle = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "data.dat"\n',
        supporting_files=[
            ("Data.dat", b"0 0 0 1 a\n"),
            ("data.DAT", b"0 0 0 1 b\n"),
        ],
    )

    report = bundle.resolve_pbed()

    assert report.references[0].status == "ambiguous"
    assert report.references[0].diagnostics[0].rule_id == "SG018"
    assert any(item.code == "DUPLICATE_BUNDLE_NAME" for item in report.diagnostics)


def test_malformed_and_generated_record_limit_reports() -> None:
    malformed = _uploaded_fixture("malformed").resolve_pbed()
    assert malformed.references[0].status == "invalid"
    assert malformed.references[0].valid_record_count == 1
    assert malformed.references[0].invalid_record_count == 3

    records = b"".join(b"0 0 0 1 u\n" for _ in range(4))
    limited_bundle = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "data.dat"\n',
        supporting_files=[("data.dat", records)],
        policy=ReferenceResolutionPolicy(
            pbed=PbedReadPolicy(max_file_size_bytes=1000, max_record_count=3)
        ),
    )
    limited = limited_bundle.resolve_pbed()
    assert limited.references[0].status == "limit_exceeded"
    assert limited.references[0].record_count == 4

    size_limited = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "data.dat"\n',
        supporting_files=[("data.dat", b"0 0 0 1 universe\n")],
        policy=ReferenceResolutionPolicy(
            pbed=PbedReadPolicy(max_file_size_bytes=10, max_record_count=10)
        ),
    ).resolve_pbed()
    assert size_limited.references[0].status == "limit_exceeded"
    assert size_limited.references[0].diagnostics[0].code == "PBED_FILE_SIZE_LIMIT"

    invalid_encoding = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "data.dat"\n',
        supporting_files=[("data.dat", b"0 0 0 1 u\n\xff\n")],
    ).resolve_pbed()
    assert invalid_encoding.references[0].status == "invalid"
    assert invalid_encoding.references[0].diagnostics[-1].code == "PBED_ENCODING"


def test_local_root_preview_then_explicit_resolution(tmp_path: Path) -> None:
    root = tmp_path / "認可ルート"
    case = root / "ケース"
    case.mkdir(parents=True)
    main = case / "main.inp"
    data = root / "配置.dat"
    main.write_text('pbed bed bg "../配置.dat"\n', encoding="utf-8")
    data.write_text("0 0 0 1 u\n", encoding="utf-8")
    project = LocalProjectSource(main_path=main, authorized_root=root)

    preview = project.preview_pbed()
    resolved = project.resolve_pbed(authorize_supporting_files=True)

    assert preview.main_name == "ケース/main.inp"
    assert preview.references[0].status == "pending_authorization"
    assert preview.references[0].pbed_data is None
    assert resolved.references[0].status == "resolved"
    assert resolved.references[0].record_count == 1


def test_local_main_growth_is_still_bounded_after_source_creation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    main = root / "main.inp"
    main.write_text("% small\n", encoding="utf-8")
    project = LocalProjectSource(
        main_path=main,
        authorized_root=root,
        policy=ReferenceResolutionPolicy(max_main_file_size_bytes=16),
    )
    main.write_bytes(b"x" * 17)

    with pytest.raises(ReferencePolicyError) as error:
        project.read_main_bytes()

    assert error.value.code == "MAIN_FILE_SIZE_LIMIT"
    assert str(root) not in str(error.value)


def test_local_target_canonicalization_failure_becomes_sanitized_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    main = root / "main.inp"
    target = root / "placements.dat"
    main.write_text('pbed bed bg "placements.dat"\n', encoding="utf-8")
    target.write_text("0 0 0 1 u\n", encoding="utf-8")
    project = LocalProjectSource(main_path=main, authorized_root=root)
    original_resolve = Path.resolve

    def fail_target_resolve(
        path: Path,
        strict: bool = False,
    ) -> Path:
        if path.name == target.name:
            raise OSError("synthetic metadata race")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_target_resolve)
    report = project.preview_pbed()

    assert report.references[0].status == "invalid"
    assert report.references[0].diagnostics[0].code == "REFERENCE_READ_FAILED"
    serialized = json.dumps(report.model_dump(mode="json"))
    assert str(root) not in serialized
    assert "synthetic metadata race" not in serialized


def test_local_root_escape_and_missing_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    main = root / "main.inp"
    main.write_text('pbed bed bg "../outside.dat"\n', encoding="utf-8")
    (tmp_path / "outside.dat").write_text("0 0 0 1 u\n", encoding="utf-8")
    project = LocalProjectSource(main_path=main, authorized_root=root)

    escaped = project.preview_pbed()

    assert escaped.references[0].status == "rejected"
    assert escaped.references[0].reference.target_name == INVALID_TARGET_MARKER

    main.write_text('pbed bed bg "missing.dat"\n', encoding="utf-8")
    missing = LocalProjectSource(main_path=main, authorized_root=root).preview_pbed()
    assert missing.references[0].status == "missing"

    target_directory = root / "directory.dat"
    target_directory.mkdir()
    main.write_text('pbed bed bg "directory.dat"\n', encoding="utf-8")
    directory_report = LocalProjectSource(
        main_path=main, authorized_root=root
    ).preview_pbed()
    assert directory_report.references[0].status == "rejected"
    assert directory_report.references[0].diagnostics[0].code == "REFERENCE_NOT_FILE"


def test_canonical_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "data.dat").write_text("0 0 0 1 u\n", encoding="utf-8")
    link = root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("The current platform does not permit creating this test symlink")
    main = root / "main.inp"
    main.write_text('pbed bed bg "linked/data.dat"\n', encoding="utf-8")

    report = LocalProjectSource(main_path=main, authorized_root=root).preview_pbed()

    assert report.references[0].status == "rejected"
    assert report.references[0].diagnostics[0].code == "REFERENCE_OUTSIDE_ROOT"


def test_local_main_must_be_inside_authorized_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    main = tmp_path / "main.inp"
    main.write_text("% synthetic\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the authorized"):
        LocalProjectSource(main_path=main, authorized_root=root)


def test_resolution_requires_no_network_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_network)
    report = _uploaded_fixture("valid").resolve_pbed()

    assert report.references[0].status == "resolved"


def test_public_report_schema_has_no_backing_path_field() -> None:
    fields = set(ExternalResolutionReport.model_fields)
    assert "path" not in fields
    assert "absolute_path" not in fields


def test_source_document_repr_omits_backing_bytes_and_paths(tmp_path: Path) -> None:
    bundle = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b"private raw input",
        supporting_files=[],
    )
    assert "private raw input" not in repr(bundle.main)

    root = tmp_path / "root"
    root.mkdir()
    main = root / "main.inp"
    main.write_text("% synthetic\n", encoding="utf-8")
    project = LocalProjectSource(main_path=main, authorized_root=root)
    assert str(root) not in repr(project.main)
