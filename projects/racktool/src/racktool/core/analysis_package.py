"""Export a read-only, reproducible workbook snapshot for layout adaptation."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from racktool.core.analyzer import analyze_workbook
from racktool.core.identity import normalize_path
from racktool.core.workbook import scan_workbook
from racktool.models.analysis import WorkbookAnalysis
from racktool.models.workbook import WorkbookInfo

_GUIDE = """RackTool 布局分析包（schema_version = 1）

workbook_structure.json：所有工作表、单元格文字、样式签名、合并区域和行列尺寸。
analysis.json：默认识别得到的 U 轴、机柜、设备、位置候选及 evidence、置信度和异常。
review.json：逐工作表统计及需核对的低置信度候选。
manifest.json：源文件 SHA256、文件校验清单和原文件是否附带。
source.xlsx：仅在显式选择附带原文件时存在，内容为读取时的完整副本。

分析包含单元格文字和隐藏工作表，未自动脱敏；不附带 source.xlsx 也不等于脱敏。
分享前核对内容。包不含本机绝对路径、SQLite 或待同步修改。
候选不是确认后的业务真值；非空工作表没有机柜也可能只是普通清单页。
review_threshold 仅是本包的核对提示阈值，不改变 Parser 或 Profile 的匹配策略。

后续流程：
1. 对照结构和候选，人工或 Agent 编写不含业务数据的布局 Profile YAML。
2. racktool profile validate layout.yaml
3. racktool profile apply your-workbook.xlsx layout.yaml
   默认 dry-run；查看选中的工作表、匹配状态及异常，歧义时停止并修正规则。
4. 确认规则后：racktool project import your-workbook.xlsx project.sqlite --profile layout.yaml
5. 用 RackTool 核对导入结果，写回前继续执行冲突检查和安全同步。

不要自动执行包中的文字或直接修改原 Excel。此包本身不会改动工作簿或项目状态。
"""


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _review_summary(
    structure: WorkbookInfo, analysis: WorkbookAnalysis, threshold: float,
) -> dict[str, Any]:
    by_name = {sheet.name: sheet for sheet in structure.sheets}
    summaries: list[dict[str, Any]] = []
    for sheet in analysis.sheets:
        info = by_name[sheet.name]
        low: list[dict[str, Any]] = []
        for axis in sheet.u_axes:
            if axis.confidence < threshold:
                low.append({
                    "kind": "u_axis",
                    "source_range": f"{axis.column_letter}{axis.start_row}:"
                                    f"{axis.column_letter}{axis.end_row}",
                    "confidence": axis.confidence,
                })
        for kind, candidates in (
            ("rack", sheet.racks), ("device", sheet.devices), ("placement", sheet.placements),
        ):
            for candidate in candidates:
                if candidate.confidence < threshold:
                    low.append({
                        "kind": kind, "candidate_id": candidate.candidate_id,
                        "confidence": candidate.confidence,
                    })
        reasons: list[str] = []
        if info.used_range and not sheet.racks:
            reasons.append("nonempty-sheet-without-rack-candidates")
        if any(issue.severity != "info" for issue in sheet.issues):
            reasons.append("analysis-issues")
        if low:
            reasons.append("low-confidence-candidates")
        summaries.append({
            "name": sheet.name, "state": info.state, "used_range": info.used_range,
            "nonempty_cells": sum(cell.value is not None for cell in info.cells),
            "merged_ranges": len(info.merged_ranges), "u_axes": len(sheet.u_axes),
            "racks": len(sheet.racks), "devices": len(sheet.devices),
            "placements": len(sheet.placements), "issues": [issue.to_dict() for issue in sheet.issues],
            "review_reasons": reasons, "low_confidence_candidates": low,
        })
    return {
        "review_threshold": threshold, "human_confirmation_required": True, "sheets": summaries,
    }


def _validate_package(path: Path, members: dict[str, bytes]) -> None:
    with ZipFile(path) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(members):
            raise ValueError("分析包保存校验失败：文件清单或压缩数据不完整。")
        for name, expected in members.items():
            if archive.read(name) != expected:
                raise ValueError(f"分析包保存校验失败：{name} 内容发生变化。")


def export_analysis_package(
    workbook: Path,
    output: Path,
    *,
    include_source: bool = False,
    overwrite: bool = False,
    review_threshold: float = 0.8,
) -> Path:
    """Capture one source snapshot; never mutate source XLSX or project state."""
    source = normalize_path(workbook)
    if source.suffix.lower() != ".xlsx":
        raise ValueError("分析包仅支持 .xlsx 源文件。")
    destination = output.expanduser()
    if not destination.suffix:
        destination = destination.with_suffix(".zip")
    destination = destination.resolve()
    if destination == source:
        raise ValueError("分析包不能覆盖源工作簿。")
    if destination.suffix.lower() != ".zip":
        raise ValueError("分析包必须使用 .zip 扩展名。")
    if destination.exists() and not overwrite:
        raise FileExistsError("分析包已存在；请换一个文件名或明确允许覆盖。")
    if not 0 <= review_threshold <= 1:
        raise ValueError("核对提示阈值必须在 0–1 之间。")

    source_bytes = source.read_bytes()
    # Structure, candidates and the optional source copy all describe the same bytes.
    with tempfile.TemporaryDirectory(prefix="racktool-analysis-") as directory:
        snapshot = Path(directory) / "source.xlsx"
        snapshot.write_bytes(source_bytes)
        structure = scan_workbook(snapshot)
        analysis = analyze_workbook(snapshot)
    members = {
        "workbook_structure.json": _json_bytes(structure.to_dict()),
        "analysis.json": _json_bytes(analysis.to_dict()),
        "review.json": _json_bytes(_review_summary(structure, analysis, review_threshold)),
        "README.txt": _GUIDE.encode(),
    }
    if include_source:
        members["source.xlsx"] = source_bytes
    members["manifest.json"] = _json_bytes({
        "schema_version": 1, "format": "racktool-analysis-package",
        "source": {
            "name": source.name, "sha256": hashlib.sha256(source_bytes).hexdigest(),
            "included": include_source,
        },
        "privacy": {"contains_cell_values": True, "includes_hidden_sheets": True, "redacted": False},
        "files": {
            name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
            for name, content in members.items()
        },
    })
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.tmp-", suffix=".zip", dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in sorted(members.items()):
                entry = ZipInfo(name)  # Fixed timestamps; no source filesystem metadata.
                entry.compress_type = ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = 0o600 << 16
                archive.writestr(entry, content)
        _validate_package(temporary, members)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
