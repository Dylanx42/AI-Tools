from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode

from racktool.profiles.schema import (
    DeviceAreaRule,
    LayoutProfile,
    ProfileLoadError,
    ProfileMatchRule,
    ProfileValidationError,
    RackRule,
    TextRule,
    UAxisRule,
)

_PROFILE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_PROFILE_BYTES = 1024 * 1024


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ProfileValidationError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ProfileValidationError(f"{path} must be a mapping with string keys")
    return value


def _check_keys(
    value: dict[str, Any], *, allowed: set[str], required: set[str], path: str
) -> None:
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise ProfileValidationError(f"{path} has unknown fields: {', '.join(unknown)}")
    if missing:
        raise ProfileValidationError(f"{path} is missing fields: {', '.join(missing)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileValidationError(f"{path} must be a non-empty string")
    return value.strip()


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ProfileValidationError(f"{path} must be a boolean")
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileValidationError(f"{path} must be a number")
    return float(value)


def _enum(value: Any, allowed: set[str], path: str) -> str:
    text = _string(value, path)
    if text not in allowed:
        raise ProfileValidationError(
            f"{path} must be one of: {', '.join(sorted(allowed))}"
        )
    return text


def _positive_integer_list(value: Any, path: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise ProfileValidationError(f"{path} must be a list")
    items: list[int] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
            raise ProfileValidationError(f"{path}[{index}] must be a positive integer")
        items.append(item)
    if len(items) != len(set(items)):
        raise ProfileValidationError(f"{path} must not contain duplicates")
    return tuple(sorted(items))


def _string_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ProfileValidationError(f"{path} must be a list")
    items = tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(items) != len(set(items)):
        raise ProfileValidationError(f"{path} must not contain duplicates")
    return items


def validate_profile_data(raw: Any) -> LayoutProfile:
    root = _mapping(raw, "profile")
    _check_keys(
        root,
        allowed={
            "schema_version",
            "profile_id",
            "name",
            "match",
            "rack",
            "u_axis",
            "device_area",
            "text",
        },
        required={
            "schema_version",
            "profile_id",
            "name",
            "match",
            "rack",
            "u_axis",
            "device_area",
        },
        path="profile",
    )

    schema_version = root["schema_version"]
    if isinstance(schema_version, bool) or schema_version != 1:
        raise ProfileValidationError("profile.schema_version must be the integer 1")
    profile_id = _string(root["profile_id"], "profile.profile_id")
    if _PROFILE_ID.fullmatch(profile_id) is None:
        raise ProfileValidationError(
            "profile.profile_id must use lowercase ASCII words separated by hyphens"
        )

    match_raw = _mapping(root["match"], "profile.match")
    _check_keys(
        match_raw,
        allowed={
            "sheet_name_regex",
            "min_confidence",
            "review_confidence",
            "allow_multiple_sheets",
            "require_issue_free",
        },
        required=set(),
        path="profile.match",
    )
    sheet_name_regex = match_raw.get("sheet_name_regex")
    if sheet_name_regex is not None:
        sheet_name_regex = _string(sheet_name_regex, "profile.match.sheet_name_regex")
        try:
            re.compile(sheet_name_regex)
        except re.error as error:
            raise ProfileValidationError(
                f"profile.match.sheet_name_regex is invalid: {error}"
            ) from error
    min_confidence = _number(match_raw.get("min_confidence", 1.0), "profile.match.min_confidence")
    review_confidence = _number(
        match_raw.get("review_confidence", 0.5),
        "profile.match.review_confidence",
    )
    if not 0 < min_confidence <= 1:
        raise ProfileValidationError("profile.match.min_confidence must be in (0, 1]")
    if not 0 <= review_confidence < min_confidence:
        raise ProfileValidationError(
            "profile.match.review_confidence must be in [0, min_confidence)"
        )

    rack_raw = _mapping(root["rack"], "profile.rack")
    _check_keys(
        rack_raw,
        allowed={"title", "height"},
        required={"title", "height"},
        path="profile.rack",
    )
    title_raw = _mapping(rack_raw["title"], "profile.rack.title")
    height_raw = _mapping(rack_raw["height"], "profile.rack.height")
    _check_keys(
        title_raw,
        allowed={"mode"},
        required={"mode"},
        path="profile.rack.title",
    )
    _check_keys(
        height_raw,
        allowed={"mode"},
        required={"mode"},
        path="profile.rack.height",
    )

    axis_raw = _mapping(root["u_axis"], "profile.u_axis")
    _check_keys(
        axis_raw,
        allowed={"direction", "pairing", "allowed_heights"},
        required=set(),
        path="profile.u_axis",
    )
    direction = _enum(
        axis_raw.get("direction", "any"),
        {"ascending", "descending", "any"},
        "profile.u_axis.direction",
    )
    pairing = _enum(
        axis_raw.get("pairing", "any"),
        {"paired", "single_axis_edge", "mixed", "any"},
        "profile.u_axis.pairing",
    )

    device_raw = _mapping(root["device_area"], "profile.device_area")
    _check_keys(
        device_raw,
        allowed={"mode"},
        required={"mode"},
        path="profile.device_area",
    )
    device_mode = _enum(
        device_raw["mode"],
        {"between_u_axes", "between_or_edge"},
        "profile.device_area.mode",
    )
    if pairing == "single_axis_edge" and device_mode == "between_u_axes":
        raise ProfileValidationError(
            "single_axis_edge pairing conflicts with between_u_axes device area"
        )
    if pairing == "mixed" and device_mode != "between_or_edge":
        raise ProfileValidationError(
            "mixed pairing requires between_or_edge device area"
        )

    text_raw = _mapping(root.get("text", {}), "profile.text")
    _check_keys(
        text_raw,
        allowed={"ignore_exact"},
        required=set(),
        path="profile.text",
    )

    return LayoutProfile(
        schema_version=1,
        profile_id=profile_id,
        name=_string(root["name"], "profile.name"),
        match=ProfileMatchRule(
            sheet_name_regex=sheet_name_regex,
            min_confidence=min_confidence,
            review_confidence=review_confidence,
            allow_multiple_sheets=_boolean(
                match_raw.get("allow_multiple_sheets", False),
                "profile.match.allow_multiple_sheets",
            ),
            require_issue_free=_boolean(
                match_raw.get("require_issue_free", True),
                "profile.match.require_issue_free",
            ),
        ),
        rack=RackRule(
            title_mode=_enum(
                title_raw["mode"],
                {"merged_cell_above_u_axis"},
                "profile.rack.title.mode",
            ),  # type: ignore[arg-type]
            height_mode=_enum(
                height_raw["mode"],
                {"infer_from_u_axis"},
                "profile.rack.height.mode",
            ),  # type: ignore[arg-type]
        ),
        u_axis=UAxisRule(
            direction=direction,  # type: ignore[arg-type]
            pairing=pairing,  # type: ignore[arg-type]
            allowed_heights=_positive_integer_list(
                axis_raw.get("allowed_heights", []),
                "profile.u_axis.allowed_heights",
            ),
        ),
        device_area=DeviceAreaRule(mode=device_mode),  # type: ignore[arg-type]
        text=TextRule(
            ignore_exact=_string_list(
                text_raw.get("ignore_exact", []),
                "profile.text.ignore_exact",
            )
        ),
    )


def load_profile(path: Path) -> LayoutProfile:
    profile_path = path.expanduser()
    if profile_path.suffix.lower() not in {".yaml", ".yml"}:
        raise ProfileLoadError("Profile files must use .yaml or .yml")
    if not profile_path.is_file():
        raise ProfileLoadError(f"Profile file is missing: {profile_path}")
    if profile_path.stat().st_size > _MAX_PROFILE_BYTES:
        raise ProfileLoadError("Profile file exceeds the 1 MiB safety limit")
    try:
        text = profile_path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise ProfileLoadError("Profile file must be UTF-8") from error
    try:
        raw = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except ProfileValidationError:
        raise
    except yaml.YAMLError as error:
        raise ProfileLoadError(f"Invalid YAML: {error}") from error
    return validate_profile_data(raw)
