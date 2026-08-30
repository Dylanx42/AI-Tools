import pytest

from racktool.models import CellRange, Placement, Rack


def test_domain_models_validate_and_serialize() -> None:
    assert Rack("rack-1", "非 48U", 12).to_dict()["height_u"] == 12
    assert Placement("p-1", "d-1", "r-1", 7, 5).to_dict()["height_u"] == 3
    assert CellRange(1, 2, 2, 3, "B1:C2").to_dict()["a1"] == "B1:C2"


def test_invalid_domain_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        Rack("rack-1", "invalid", 0)
    with pytest.raises(ValueError):
        CellRange(2, 1, 1, 1, "A2:A1")
