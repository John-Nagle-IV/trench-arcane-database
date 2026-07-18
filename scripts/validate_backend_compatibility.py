#!/usr/bin/env python3
"""Prove fixture and generated-schema compatibility with a clean backend checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def manage_path(backend_root: Path) -> Path:
    candidates = (
        backend_root / "manage.py",
        backend_root / "trench_backend/manage.py",
        backend_root / "services/backend/trench_backend/manage.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("could not locate manage.py; pass the backend repository root")


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def parse_last_json_line(output: str) -> Any:
    for line in reversed(output.splitlines()):
        if line.strip():
            return json.loads(line)
    raise ValueError("command did not produce JSON output")


def canonicalize_schema(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonicalize_schema(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        items = [canonicalize_schema(item) for item in value]
        return sorted(items) if all(isinstance(item, str) for item in items) else items
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-root", type=Path, required=True)
    parser.add_argument("--backend-python", default=sys.executable)
    parser.add_argument("--data-root", type=Path, default=ROOT)
    args = parser.parse_args()

    backend_root = args.backend_root.resolve()
    data_root = args.data_root.resolve()
    manage = manage_path(backend_root)
    vocabulary_reference = data_root / "fixtures/reference/migration-vocabularies.json"
    dynamic_schema = data_root / "schemas/card-effect.schema.json"
    if not vocabulary_reference.is_file() or not dynamic_schema.is_file():
        raise FileNotFoundError("database vocabulary reference or dynamic schema is missing")
    expected_vocabularies = json.loads(vocabulary_reference.read_text(encoding="utf-8"))["vocabularies"]

    with tempfile.TemporaryDirectory(prefix="trench-arcane-fixture-") as temporary_dir:
        environment = os.environ.copy()
        environment.update(
            {
                "USE_SQLITE_FOR_TESTS": "true",
                "SQLITE_DATABASE_PATH": str(Path(temporary_dir) / "backend.sqlite3"),
            }
        )
        command_prefix = [args.backend_python, str(manage)]
        run([*command_prefix, "migrate", "--noinput"], cwd=manage.parent, env=environment)
        migration_state = run([*command_prefix, "showmigrations", "cards"], cwd=manage.parent, env=environment)
        if "[X] 0001_initial" not in migration_state:
            raise RuntimeError("backend did not apply cards.0001_initial")
        vocabulary_dump = run(
            [
                *command_prefix,
                "shell",
                "-c",
                "from django.apps import apps; import json; names = "
                + repr(sorted(expected_vocabularies))
                + "; print(json.dumps({name: list(apps.get_model('cards', name).objects.values_list('name', flat=True)) for name in names}, sort_keys=True))",
            ],
            cwd=manage.parent,
            env=environment,
        )
        actual_vocabularies = parse_last_json_line(vocabulary_dump)
        for model, expected_names in expected_vocabularies.items():
            missing = sorted(set(expected_names) - set(actual_vocabularies[model]))
            if missing:
                raise RuntimeError(f"backend migration did not provide {model} values: {missing}")
        generated_schema = run(
            [
                *command_prefix,
                "shell",
                "-c",
                "import json; from engine.effect.schema import build_effect_schema; print(json.dumps(build_effect_schema(), sort_keys=True))",
            ],
            cwd=manage.parent,
            env=environment,
        )
        expected = hashlib.sha256(dynamic_schema.read_bytes()).hexdigest()
        canonical_schema = json.dumps(canonicalize_schema(parse_last_json_line(generated_schema)), indent=2, sort_keys=True) + "\n"
        actual = hashlib.sha256(canonical_schema.encode()).hexdigest()
        if actual != expected:
            raise RuntimeError("database dynamic effect schema differs from the backend-generated API schema")

    print("clean backend migration, vocabulary-reference, and dynamic effect schema compatibility passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
