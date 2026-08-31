from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"


def _run_clean_python(script: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        environment.pop(name, None)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    command = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC_ROOT)!r})\n"
        f"{script}\n"
    )
    return subprocess.run(
        [sys.executable, "-I", "-B", "-c", command],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


IMPORT_CASES = (
    """
import racktool.profiles as profiles
assert {
    "apply_profile", "analyze_profiled_workbook", "load_profile"
}.issubset(set(profiles.__all__))
assert all(hasattr(profiles, name) for name in profiles.__all__)
""",
    """
from racktool.profiles import apply_profile, analyze_profiled_workbook, load_profile
assert callable(apply_profile)
assert callable(analyze_profiled_workbook)
assert callable(load_profile)
""",
    """
import racktool.core as core
assert all(hasattr(core, name) for name in core.__all__)
""",
    """
import racktool.profiles
import racktool.core
""",
    """
import racktool.core
import racktool.profiles
""",
    """
import racktool.profiles.apply
import racktool.core
""",
    """
import racktool.core
import racktool.profiles.apply
""",
)


@pytest.mark.parametrize("script", IMPORT_CASES)
def test_public_packages_import_in_any_order_in_clean_interpreter(
    script: str,
    tmp_path: Path,
) -> None:
    result = _run_clean_python(script, tmp_path)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "test_path",
    (
        "tests/unit/test_profiles.py",
        "tests/integration/test_profile_matching.py",
    ),
)
def test_profile_gate_modules_run_independently_in_clean_interpreter(
    test_path: str,
    tmp_path: Path,
) -> None:
    target = PROJECT_ROOT / test_path
    pytest_temp = tmp_path / "pytest-temp"
    script = (
        "import pytest\n"
        "raise SystemExit(pytest.main([\n"
        "    '-q', '-p', 'no:cacheprovider',\n"
        f"    '--basetemp={pytest_temp}',\n"
        f"    '-c', {str(PROJECT_ROOT / 'pyproject.toml')!r},\n"
        f"    {str(target)!r},\n"
        "]))"
    )

    result = _run_clean_python(script, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
