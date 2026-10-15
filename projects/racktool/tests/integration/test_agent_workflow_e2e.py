"""Independent process-boundary regression, not actual Agent compatibility evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_scripted_conversation_and_table_workflow(tmp_path: Path) -> None:
    project = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "evidence with spaces"
    environment = dict(os.environ, PYTHONPATH=str(project / "src"),
                       PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
    result = subprocess.run([
        sys.executable, str(project / "scripts" / "verify_skill_workflows.py"),
        "--output", str(evidence),
    ], env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "passed"
    assert len(report["checks"]) == 6
    assert report["agent_manual_acceptance"] == {"Codex": "pending", "WorkBuddy": "pending", "TRAE": "pending"}
    assert (evidence / "events.json").exists()
