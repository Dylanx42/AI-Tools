"""Generate and verify a public synthetic rack/editing corpus for review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from tests.corpus_checks import run_draft_case, run_layout_case
from tests.layout_corpus import DRAFT_CASES, LAYOUT_CASES


def main() -> int:
    parser = argparse.ArgumentParser(description="生成并验证 144 种合成布局和 120 种新建项目编辑场景")
    parser.add_argument("--output", type=Path, required=True, help="新的输出目录，含样本和报告")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists() and not output.is_dir():
        parser.error("输出路径必须是目录。")
    if output.exists() and any(output.iterdir()):
        parser.error("输出目录已有内容，请选择一个新的目录；不会覆盖历史测试证据。")
    archive_path = output.with_name(f"{output.name}.zip")
    if archive_path.exists():
        parser.error("同名 ZIP 已存在，请选择新的输出目录名。")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    started = time.monotonic()
    previous_storage = os.environ.get("RACKTOOL_DATA_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="racktool-corpus-storage-") as storage:
            os.environ["RACKTOOL_DATA_DIR"] = storage
            for kind, cases, exercise in (
                ("layouts", LAYOUT_CASES, run_layout_case), ("drafts", DRAFT_CASES, run_draft_case),
            ):
                for index, case in enumerate(cases, start=1):
                    directory = output / kind / case.case_id
                    try:
                        result = exercise(case, directory)
                    except Exception as error:  # noqa: BLE001
                        result = {"case_id": case.case_id, "kind": kind, "passed": False,
                                  "error": f"{type(error).__name__}: {error}"}
                    if kind == "layouts" and result["passed"]:
                        facts = json.loads((directory / "expected.json").read_text(encoding="utf-8"))
                        geometry = {"racks": facts["racks"], "axis_label_format": facts["case"]["label"]}
                        result["structural_sha256"] = hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest()
                    results.append(result)
                    (directory / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                    if index % 12 == 0 or not result["passed"]:
                        print(f"{kind}: {index}/{len(cases)}, passed={sum(row['passed'] for row in results)}", flush=True)
    finally:
        if previous_storage is None:
            os.environ.pop("RACKTOOL_DATA_DIR", None)
        else:
            os.environ["RACKTOOL_DATA_DIR"] = previous_storage

    passed = sum(result["passed"] for result in results)
    unique_structures = len({result["structural_sha256"] for result in results if "structural_sha256" in result})
    summary = {
        "schema_version": 1, "synthetic": True,
        "layout_combinations": len(LAYOUT_CASES), "structural_variants_passed": unique_structures,
        "fundamental_layout_families": len({case.family for case in LAYOUT_CASES}), "draft_editing_scenarios": len(DRAFT_CASES),
        "passed": passed, "failed": len(results) - passed,
        "successful_edit_operations": sum(result.get("committed_edits", 0) for result in results),
        "rejected_invalid_edits": sum(result.get("rejected_edits", 0) for result in results),
        "duration_seconds": round(time.monotonic() - started, 2),
        "real_golden_evidence": False, "desktop_excel_wps_validation": "pending",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = sorted({key for result in results for key in result})
    with (output / "results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    family_totals = Counter(case.family for case in LAYOUT_CASES)
    family_passes = Counter(result.get("family") for result in results if result["passed"] and result.get("kind") == "layout")
    report = ["# RackTool 合成机柜图与编辑验证报告", "",
              f"{len(LAYOUT_CASES)} 种布局组合，{len(DRAFT_CASES)} 种新建项目场景；通过 {passed}，失败 {len(results) - passed}。",
              "", "布局组合来自 6 类结构 × 2 个方向 × 4 个高度 × 3 种 U 标签；并非 144 种独立行业标准。",
              "新建项目场景来自 5 种柜数 × 4 个高度 × 3 个初始占用比例 × 2 种文本形式。",
              "", "| 布局结构 | 通过 | 总数 |", "| --- | ---: | ---: |"]
    report.extend(f"| {family} | {family_passes[family]} | {count} |" for family, count in family_totals.items())
    report.extend(["", f"成功编辑 {summary['successful_edit_operations']} 次，拒绝无效编辑 {summary['rejected_invalid_edits']} 次。",
                   "每个布局验证导入、移动、新增、改名、备份、冲突拒绝、重扫身份与标准导出；核对未触及的",
                   "单元格、标尺、尺寸、隐藏页、备注、链接、命名区域及原有公式。新项目验证同名设备、文字编辑、",
                   "跨柜移动/调整高度、越界/重叠拒绝、重启读取和导出再识别。",
                   "", "所有数据均为生成的 synthetic fixture。expected 来自构造事实，未使用 Parser 输出生成答案。",
                   "这些结果不替代真实私有 Golden、Microsoft Excel/WPS 或桌面人工验收。", ""])
    (output / "report.md").write_text("\n".join(report), encoding="utf-8")
    (output / "README.md").write_text(
        "# RackTool 合成测试样本\n\n"
        "layouts/ 每例含原始 source.xlsx、edited.xlsx、standard-export.xlsx、独立 expected JSON 和验证记录。\n"
        "fixed-profile 系列附 profile.yaml；它需要该布局规则，不能宣称默认识别直接通过。\n"
        "drafts/ 每例含编辑后 Excel、可续用的新建 SQLite、独立预期和验证记录。\n"
        "导入项目的 SQLite 绑定云端路径，因此不放入 ZIP；在你自己的电脑上可从 source.xlsx 或 edited.xlsx 重新导入。\n"
        "report.md / summary.json / results.csv 为本次实测结果。样本全部是合成数据，不是真实业务文件。\n",
        encoding="utf-8",
    )
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(output)
            if path.suffix == ".sqlite" and relative.parts[0] == "layouts":
                continue
            archive.write(path, relative.as_posix())
    print(json.dumps({**summary, "archive": str(archive_path)}, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 and unique_structures >= 100 else 1


if __name__ == "__main__":
    raise SystemExit(main())
