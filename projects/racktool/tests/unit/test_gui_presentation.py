from __future__ import annotations

from racktool.gui.presentation import (
    cell_display_text,
    friendly_conflict_text,
    friendly_exception,
    friendly_issue,
)


def test_friendly_issue_uses_chinese_and_keeps_code_as_technical_detail() -> None:
    copy = friendly_issue(
        "unresolved-u-axis",
        "Found a U-axis without a rack title",
        "warning",
    )

    assert copy["level"] == "提醒（不阻止同步）"
    assert "U 位" in copy["title"]
    assert "重新扫描" in copy["guidance"]
    assert "unresolved-u-axis" not in copy["title"]
    assert "unresolved-u-axis" not in copy["guidance"]
    assert copy["technical_detail"].startswith("unresolved-u-axis:")


def test_friendly_issue_groups_unknown_codes_into_chinese_categories() -> None:
    copy = friendly_issue("ambiguous-something-new", "could not match device", "error")

    assert copy["level"] == "需要处理"
    assert "无法唯一确认" in copy["title"]
    assert "重新扫描" in copy["guidance"]
    assert "ambiguous-something-new" in copy["technical_detail"]


def test_cell_display_text_preserves_excel_newlines() -> None:
    assert cell_display_text("交换机\r\n核心\r管理口") == "交换机\n核心\n管理口"


def test_friendly_exception_hides_raw_python_errors() -> None:
    message = friendly_exception(FileNotFoundError("missing.xlsx"))

    assert "找不到" in message
    assert "missing.xlsx" not in message


def test_friendly_conflict_text_joins_title_and_guidance() -> None:
    text = friendly_conflict_text("target-u-occupied", "Target U is occupied")

    assert "目标 U 位已经有设备" in text
    assert "空闲" in text
    assert "target-u-occupied" not in text
