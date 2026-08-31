from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any

from racktool.profiles.loader import validate_profile_data
from racktool.profiles.schema import LayoutProfile, ProfileValidationError

PROFILE_METADATA_KEY = "layout_profile"
_PROFILE_RECORD_SCHEMA_VERSION = 1


def canonical_profile_payload(profile: LayoutProfile) -> dict[str, Any]:
    """Return normalized, schema-shaped semantics for project persistence."""
    match: dict[str, Any] = {
        "min_confidence": profile.match.min_confidence,
        "review_confidence": profile.match.review_confidence,
        "allow_multiple_sheets": profile.match.allow_multiple_sheets,
        "require_issue_free": profile.match.require_issue_free,
    }
    if profile.match.sheet_name_regex is not None:
        match["sheet_name_regex"] = profile.match.sheet_name_regex

    title: dict[str, Any] = {"mode": profile.rack.title_mode}
    if profile.rack.title_range is not None:
        title["range"] = profile.rack.title_range

    u_axis: dict[str, Any] = {
        "direction": profile.u_axis.direction,
        "pairing": profile.u_axis.pairing,
        "allowed_heights": list(profile.u_axis.allowed_heights),
        "max_missing_rows": profile.u_axis.max_missing_rows,
    }
    for key, value in (
        ("left_column", profile.u_axis.left_column),
        ("right_column", profile.u_axis.right_column),
        ("start_row", profile.u_axis.start_row),
        ("end_row", profile.u_axis.end_row),
    ):
        if value is not None:
            u_axis[key] = value

    device_area: dict[str, Any] = {"mode": profile.device_area.mode}
    if profile.device_area.source_range is not None:
        device_area["range"] = profile.device_area.source_range

    return {
        "schema_version": profile.schema_version,
        "profile_id": profile.profile_id,
        "name": profile.name,
        "match": match,
        "rack": {
            "title": title,
            "height": {"mode": profile.rack.height_mode},
        },
        "u_axis": u_axis,
        "device_area": device_area,
        "text": {"ignore_exact": list(profile.text.ignore_exact)},
    }


def normalize_profile(profile: LayoutProfile) -> LayoutProfile:
    """Revalidate directly constructed dataclasses through the schema."""
    return validate_profile_data(canonical_profile_payload(profile))


def _canonical_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ProfileValidationError("Stored Profile payload is not canonical JSON") from error


def profile_payload_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def make_profile_record(profile: LayoutProfile) -> dict[str, Any]:
    normalized = normalize_profile(profile)
    payload = canonical_profile_payload(normalized)
    return {
        "schema_version": _PROFILE_RECORD_SCHEMA_VERSION,
        "payload_sha256": profile_payload_sha256(payload),
        "payload": payload,
    }


def load_profile_record(record: object) -> LayoutProfile:
    if not isinstance(record, dict) or set(record) != {
        "schema_version",
        "payload_sha256",
        "payload",
    }:
        raise ProfileValidationError("Stored Profile record is missing or has unknown fields")
    if record["schema_version"] != _PROFILE_RECORD_SCHEMA_VERSION:
        raise ProfileValidationError("Stored Profile record schema is unsupported")
    expected_hash = record["payload_sha256"]
    payload = record["payload"]
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ProfileValidationError("Stored Profile hash is invalid")
    if not isinstance(payload, dict):
        raise ProfileValidationError("Stored Profile payload must be an object")
    actual_hash = profile_payload_sha256(payload)
    if not hmac.compare_digest(actual_hash, expected_hash):
        raise ProfileValidationError("Stored Profile payload hash mismatch")
    profile = validate_profile_data(payload)
    if canonical_profile_payload(profile) != payload:
        raise ProfileValidationError("Stored Profile payload is not normalized")
    return profile


def metadata_with_profile(
    metadata: Mapping[str, Any],
    profile: LayoutProfile | None,
) -> dict[str, Any]:
    result = dict(metadata)
    result.pop(PROFILE_METADATA_KEY, None)
    if profile is not None:
        result[PROFILE_METADATA_KEY] = make_profile_record(profile)
    return result


def load_stored_profile(
    profile_id: str | None,
    metadata: Mapping[str, Any],
) -> LayoutProfile | None:
    has_record = PROFILE_METADATA_KEY in metadata
    if profile_id is None:
        if has_record:
            raise ProfileValidationError(
                "Project has stored Profile semantics without a profile_id"
            )
        return None
    if not has_record:
        raise ProfileValidationError("Project Profile metadata is missing")
    profile = load_profile_record(metadata[PROFILE_METADATA_KEY])
    if profile.profile_id != profile_id:
        raise ProfileValidationError("Project profile_id does not match stored Profile")
    return profile
