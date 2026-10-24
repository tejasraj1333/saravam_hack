"""Lightweight local JSON file storage — used when MongoDB is unavailable.

Each collection maps to a single JSON file under the data/ directory.
Thread-safety is acceptable for a single-user hackathon demo.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class LocalStore:
    """Simple file-backed key-value store, one JSON file per collection."""

    def __init__(self) -> None:
        self._base = get_settings().data_dir

    def _path(self, collection: str) -> Path:
        return self._base / f"{collection}.json"

    def _load(self, collection: str) -> dict[str, Any]:
        p = self._path(collection)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Corrupt JSON in %s, resetting.", p)
        return {}

    def _save(self, collection: str, data: dict[str, Any]) -> None:
        p = self._path(collection)
        p.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── CRUD ───────────────────────────────────────────────────

    def insert(self, collection: str, key: str, value: dict) -> None:
        data = self._load(collection)
        data[key] = value
        self._save(collection, data)

    def get(self, collection: str, key: str) -> dict | None:
        return self._load(collection).get(key)

    def get_all(self, collection: str) -> list[dict]:
        return list(self._load(collection).values())

    def update(self, collection: str, key: str, updates: dict) -> bool:
        data = self._load(collection)
        if key not in data:
            return False
        data[key].update(updates)
        self._save(collection, data)
        return True

    def delete(self, collection: str, key: str) -> bool:
        data = self._load(collection)
        if key not in data:
            return False
        del data[key]
        self._save(collection, data)
        return True

    def query(self, collection: str, field: str, value: Any) -> list[dict]:
        """Return all records where record[field] == value."""
        return [r for r in self._load(collection).values() if r.get(field) == value]


# Singleton
_store: LocalStore | None = None


def get_local_store() -> LocalStore:
    global _store
    if _store is None:
        _store = LocalStore()
    return _store
