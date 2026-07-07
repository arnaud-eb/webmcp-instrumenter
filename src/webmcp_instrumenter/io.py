"""JSON load/save + contract-schema validation (T008).

Stage boundaries are plain JSON files. Validation uses the authoritative JSON
Schemas under the active feature's `contracts/` directory (single source of
truth). If the schema can't be located (e.g. running outside the repo), the
validation step soft-skips with a warning rather than failing the pipeline.
"""

from __future__ import annotations

import json
import sys
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema


def load_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _warn(msg: str) -> None:
    print(f"[io] {msg}", file=sys.stderr)


@cache
def _repo_root() -> Path | None:
    """Walk up from this file looking for a `.specify/` marker."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".specify").is_dir():
            return parent
    return None


@cache
def _contracts_dir() -> Path | None:
    root = _repo_root()
    if root is None:
        return None
    feature_json = root / ".specify" / "feature.json"
    if not feature_json.is_file():
        return None
    try:
        feature_dir = json.loads(feature_json.read_text())["feature_directory"]
    except (json.JSONDecodeError, KeyError):
        return None
    contracts = root / feature_dir / "contracts"
    return contracts if contracts.is_dir() else None


def contract_schema(name: str) -> dict[str, Any] | None:
    """Load a contract JSON Schema by filename, or None if unavailable."""
    contracts = _contracts_dir()
    if contracts is None:
        return None
    schema_path = contracts / name
    if not schema_path.is_file():
        return None
    return load_json(schema_path)


def validate_against(data: Any, schema_name: str) -> None:
    """Validate `data` against a contract schema.

    Raises jsonschema.ValidationError on mismatch. Soft-skips (with a warning)
    if the schema file cannot be located.
    """
    schema = contract_schema(schema_name)
    if schema is None:
        _warn(f"schema {schema_name!r} not found — skipping validation")
        return
    jsonschema.validate(instance=data, schema=schema)
