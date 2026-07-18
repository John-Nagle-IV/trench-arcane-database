#!/usr/bin/env python3
"""Validate portable database assets without importing the backend repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_json_documents(root: Path) -> list[Path]:
    paths = sorted(
        path
        for path in root.glob("**/*.json")
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    )
    for path in paths:
        load_json(path)
    if not paths:
        raise ValueError("no JSON assets found")
    return paths


def validate_reference_vocabulary(path: Path) -> None:
    document = load_json(path)
    expected_models = {
        "RuleAction",
        "RuleCondition",
        "RuleKeyword",
        "RuleResourceType",
        "RuleTargetMode",
        "RuleTargetOwner",
        "RuleTargetType",
        "RuleTrigger",
        "RuleZone",
    }
    if document.get("format") != "trench-arcane.migration-vocabulary-reference/v1":
        raise ValueError("unexpected effect vocabulary reference format")
    vocabularies = document.get("vocabularies")
    if not isinstance(vocabularies, dict) or set(vocabularies) != expected_models:
        raise ValueError("effect vocabulary reference has an unexpected model set")
    for model, values in vocabularies.items():
        if not isinstance(values, list) or not values or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"invalid vocabulary values for {model}")
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate vocabulary values for {model}")


def validate_effect_schemas(root: Path) -> None:
    dynamic_schema = load_json(root / "schemas/card-effect.schema.json")
    if dynamic_schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
        raise ValueError("card-effect schema must be the backend draft-07 dynamic schema")
    if dynamic_schema.get("title") != "Trench Arcane Dynamic Effect Schema":
        raise ValueError("card-effect schema title does not match the backend contract")
    Draft7Validator.check_schema(dynamic_schema)

    legacy_schema = load_json(root / "fixtures/reference/legacy-card-effect.schema.json")
    Draft202012Validator.check_schema(legacy_schema)
    validator = Draft202012Validator(legacy_schema)
    for example in legacy_schema.get("examples", []):
        errors = list(validator.iter_errors(example["effect"]))
        if errors:
            raise ValueError(f"legacy schema example {example.get('name')!r} is invalid")
    for sample in load_json(root / "fixtures/reference/invalid-effect-samples.json"):
        if not list(validator.iter_errors(sample["effect"])):
            raise ValueError(f"legacy invalid sample {sample.get('name')!r} was accepted")

    deck_schema = load_json(root / "schemas/deck-constraints.schema.json")
    if deck_schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
        raise ValueError("deck constraints schema must use JSON Schema draft-07")
    Draft7Validator.check_schema(deck_schema)


def validate_canonical_cards(path: Path) -> None:
    document = load_json(path)
    cards = document.get("cards")
    if document.get("version") != "1.0.0-CANONICAL" or not isinstance(cards, dict) or not cards:
        raise ValueError("canonical card corpus must be a non-empty 1.0.0-CANONICAL document")
    for name, card in cards.items():
        if not isinstance(name, str) or not name or not isinstance(card, dict):
            raise ValueError("canonical card corpus has an invalid card entry")
        if card.get("type") not in {"Unit", "Building", "Command", "Resource", "CommandCenter"}:
            raise ValueError(f"canonical card {name!r} has an unsupported type")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    documents = validate_json_documents(root)
    validate_reference_vocabulary(root / "fixtures/reference/migration-vocabularies.json")
    validate_effect_schemas(root)
    validate_canonical_cards(root / "fixtures/canonical/canonical_cards.json")
    print(f"validated {len(documents)} JSON assets; schemas, fixture identities, and canonical corpus are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
