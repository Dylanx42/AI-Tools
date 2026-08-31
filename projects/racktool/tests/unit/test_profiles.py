from __future__ import annotations

from pathlib import Path

import pytest

from racktool.profiles import (
    ProfileLoadError,
    ProfileValidationError,
    load_profile,
    validate_profile_data,
)

VALID_PROFILE = {
    "schema_version": 1,
    "profile_id": "generic-dual-axis",
    "name": "Generic dual U-axis rack layout",
    "match": {"min_confidence": 1.0, "review_confidence": 0.5},
    "rack": {
        "title": {"mode": "merged_cell_above_u_axis"},
        "height": {"mode": "infer_from_u_axis"},
    },
    "u_axis": {
        "direction": "descending",
        "pairing": "paired",
        "allowed_heights": [12, 47],
    },
    "device_area": {"mode": "between_u_axes"},
}


def test_valid_profile_loads() -> None:
    profile = validate_profile_data(VALID_PROFILE)
    assert profile.profile_id == "generic-dual-axis"
    assert profile.u_axis.allowed_heights == (12, 47)


def test_unknown_field_is_rejected() -> None:
    payload = dict(VALID_PROFILE)
    payload["execute"] = "rm -rf /"
    with pytest.raises(ProfileValidationError, match="unknown fields"):
        validate_profile_data(payload)


def test_conflicting_pairing_and_device_area_are_rejected() -> None:
    payload = {
        **VALID_PROFILE,
        "u_axis": {"pairing": "single_axis_edge"},
        "device_area": {"mode": "between_u_axes"},
    }
    with pytest.raises(ProfileValidationError, match="conflicts"):
        validate_profile_data(payload)


def test_invalid_regex_is_rejected() -> None:
    payload = {
        **VALID_PROFILE,
        "match": {"sheet_name_regex": "("},
    }
    with pytest.raises(ProfileValidationError, match="sheet_name_regex"):
        validate_profile_data(payload)


def test_non_yaml_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "not-a-profile.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ProfileLoadError, match=".yaml"):
        load_profile(path)


def test_duplicate_yaml_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.yaml"
    path.write_text(
        "schema_version: 1\nprofile_id: x\nprofile_id: y\nname: Dup\n"
        "match: {}\nrack:\n  title:\n    mode: merged_cell_above_u_axis\n"
        "  height:\n    mode: infer_from_u_axis\nu_axis: {}\n"
        "device_area:\n  mode: between_u_axes\n",
        encoding="utf-8",
    )
    with pytest.raises(ProfileValidationError, match="Duplicate YAML key"):
        load_profile(path)


def test_bundled_profiles_validate() -> None:
    root = Path(__file__).resolve().parents[2] / "src/racktool/profiles"
    for name in ("generic-dual-axis.yaml", "generic-mixed-axis.yaml"):
        profile = load_profile(root / name)
        assert profile.schema_version == 1
        assert profile.u_axis.allowed_heights == ()


def test_fixed_coordinate_profile_normalizes_columns_and_ranges() -> None:
    payload = {
        **VALID_PROFILE,
        "rack": {
            "title": {"mode": "fixed_range", "range": "$G$2:$H$2"},
            "height": {"mode": "infer_from_u_axis"},
        },
        "u_axis": {
            "direction": "descending",
            "pairing": "paired",
            "left_column": "F",
            "right_column": "I",
            "start_row": 4,
            "end_row": 11,
            "max_missing_rows": 0,
        },
        "device_area": {"mode": "fixed_range", "range": "$G$4:$H$11"},
    }

    profile = validate_profile_data(payload)

    assert profile.rack.title_range == "G2:H2"
    assert profile.u_axis.left_column == 6
    assert profile.u_axis.right_column == 9
    assert profile.u_axis.start_row == 4
    assert profile.u_axis.end_row == 11
    assert profile.u_axis.max_missing_rows == 0
    assert profile.device_area.source_range == "G4:H11"


def test_incomplete_or_ambiguous_coordinate_profile_is_rejected() -> None:
    missing_right = {
        **VALID_PROFILE,
        "rack": {
            "title": {"mode": "fixed_range", "range": "G2:H2"},
            "height": {"mode": "infer_from_u_axis"},
        },
        "u_axis": {
            "direction": "descending",
            "pairing": "paired",
            "left_column": "F",
            "start_row": 4,
            "end_row": 11,
        },
        "device_area": {"mode": "fixed_range", "range": "G4:H11"},
    }
    with pytest.raises(ProfileValidationError, match="requires right_column"):
        validate_profile_data(missing_right)

    excessive_gap = {
        **VALID_PROFILE,
        "u_axis": {"max_missing_rows": 2},
    }
    with pytest.raises(ProfileValidationError, match="must be 0 or 1"):
        validate_profile_data(excessive_gap)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("left_column", 16_385, "positive column number or letter"),
        ("left_column", "XFE", "exceeds the XLSX column limit"),
    ],
)
def test_coordinate_profile_rejects_columns_outside_xlsx_limits(
    field: str, value: object, message: str
) -> None:
    payload = {
        **VALID_PROFILE,
        "rack": {
            "title": {"mode": "fixed_range", "range": "B1:C1"},
            "height": {"mode": "infer_from_u_axis"},
        },
        "u_axis": {
            "direction": "descending",
            "pairing": "single_axis_edge",
            field: value,
            "start_row": 2,
            "end_row": 5,
        },
        "device_area": {"mode": "fixed_range", "range": "B2:C5"},
    }

    with pytest.raises(ProfileValidationError, match=message):
        validate_profile_data(payload)


@pytest.mark.parametrize(
    "source_range",
    ["H4:G3", "G1:XFE4", "G1:H1048577"],
)
def test_coordinate_profile_rejects_invalid_bounded_ranges(source_range: str) -> None:
    payload = {
        **VALID_PROFILE,
        "device_area": {"mode": "fixed_range", "range": source_range},
    }

    with pytest.raises(ProfileValidationError):
        validate_profile_data(payload)


def test_axis_coordinates_without_fixed_fallback_are_rejected() -> None:
    payload = {
        **VALID_PROFILE,
        "u_axis": {
            "direction": "descending",
            "pairing": "paired",
            "left_column": "A",
            "right_column": "C",
            "start_row": 2,
            "end_row": 13,
        },
    }

    with pytest.raises(ProfileValidationError, match="require fixed coordinate fallback"):
        validate_profile_data(payload)
