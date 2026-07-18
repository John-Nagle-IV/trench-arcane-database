from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portable_asset_validator_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_assets.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "validated 8 JSON assets" in result.stdout
