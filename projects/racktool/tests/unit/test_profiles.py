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
