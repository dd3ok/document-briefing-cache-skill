from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class CacheReadResult:
    status: Literal["hit", "miss", "expired", "corrupt"]
    value: Any | None = None


@dataclass
class CacheOperationResult:
    entries_deleted: int = 0
    bytes_deleted: int = 0
    entries_scanned: int = 0
    dry_run: bool = False


class JsonFileCache:
    """Small JSON cache for local deterministic skill runs."""

    def __init__(self, cache_dir: str | Path, namespace: str):
        self.root = Path(cache_dir) / namespace
        self.root.mkdir(parents=True, exist_ok=True)
        self.namespace = namespace
        self._created_paths: set[Path] = set()

    def path_for(self, key: str) -> Path:
        safe = "".join(ch for ch in key if ch.isalnum() or ch in "-_")
        return self.root / f"{safe}.json"

    def get_json(self, key: str) -> dict[str, Any] | None:
        result = self.get_json_with_status(key)
        return result.value if result.status == "hit" else None

    def get_json_with_status(self, key: str, update_accessed: bool = True) -> CacheReadResult:
        path = self.path_for(key)
        if not path.exists():
            return CacheReadResult(status="miss")
        entry = self._read_entry(path)
        if entry is None:
            return CacheReadResult(status="corrupt")
        if self._is_expired(entry):
            return CacheReadResult(status="expired")
        if self._is_envelope(entry):
            if update_accessed:
                entry["last_accessed_at"] = _now_iso()
                self._write_entry(path, entry)
            return CacheReadResult(status="hit", value=entry.get("payload"))
        return CacheReadResult(status="hit", value=entry)

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        path = self.path_for(key)
        envelope = {
            "cache_version": "1.0",
            "namespace": self.namespace,
            "key": key,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "last_accessed_at": _now_iso(),
            "expires_at": _expires_at_iso(ttl_seconds),
            "payload": value,
        }
        self._write_entry(path, envelope)
        self._created_paths.add(path)

    def get_model(self, key: str, model: type[T]) -> T | None:
        value = self.get_json(key)
        if value is None:
            return None
        return model.model_validate(value)

    def get_model_with_status(self, key: str, model: type[T], update_accessed: bool = True) -> tuple[T | None, str]:
        result = self.get_json_with_status(key, update_accessed=update_accessed)
        if result.status != "hit":
            return None, result.status
        return model.model_validate(result.value), result.status

    def set_model(self, key: str, value: BaseModel, ttl_seconds: int | None = None) -> None:
        self.set_json(key, value.model_dump(mode="json"), ttl_seconds=ttl_seconds)

    def get_text(self, key: str) -> str | None:
        result = self.get_text_with_status(key)
        return result.value if result.status == "hit" else None

    def get_text_with_status(self, key: str, update_accessed: bool = True) -> CacheReadResult:
        result = self.get_json_with_status(key, update_accessed=update_accessed)
        if result.status != "hit":
            return result
        return CacheReadResult(status="hit", value=(result.value or {}).get("output"))

    def set_text(self, key: str, output: str, ttl_seconds: int | None = None) -> None:
        self.set_json(key, {"output": output}, ttl_seconds=ttl_seconds)

    def prune(self, older_than_seconds: int | None = None, dry_run: bool = False) -> CacheOperationResult:
        result = CacheOperationResult(dry_run=dry_run)
        now = datetime.now(timezone.utc)
        for path in self.root.glob("*.json"):
            result.entries_scanned += 1
            entry = self._read_entry(path)
            expired = entry is None or self._is_expired(entry)
            older = False
            if older_than_seconds is not None:
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                older = modified <= now - timedelta(seconds=older_than_seconds)
            if expired or older:
                result.entries_deleted += 1
                result.bytes_deleted += path.stat().st_size
                if not dry_run:
                    path.unlink(missing_ok=True)
        return result

    def clear(self, dry_run: bool = False) -> CacheOperationResult:
        result = CacheOperationResult(dry_run=dry_run)
        for path in self.root.glob("*.json"):
            result.entries_scanned += 1
            result.entries_deleted += 1
            result.bytes_deleted += path.stat().st_size
            if not dry_run:
                path.unlink(missing_ok=True)
        return result

    def clear_created(self) -> CacheOperationResult:
        result = CacheOperationResult()
        for path in list(self._created_paths):
            if path.exists():
                result.entries_scanned += 1
                result.entries_deleted += 1
                result.bytes_deleted += path.stat().st_size
                path.unlink(missing_ok=True)
        self._created_paths.clear()
        return result

    def stats(self) -> dict[str, Any]:
        files = list(self.root.glob("*.json"))
        return {
            "namespace": self.namespace,
            "entries": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "path": str(self.root),
        }

    def _read_entry(self, path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as f:
                value = json.load(f)
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_entry(self, path: Path, value: dict[str, Any]) -> None:
        tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)

    def _is_envelope(self, value: dict[str, Any]) -> bool:
        return value.get("cache_version") == "1.0" and "payload" in value

    def _is_expired(self, value: dict[str, Any]) -> bool:
        if not self._is_envelope(value):
            return False
        expires_at = value.get("expires_at")
        if not expires_at:
            return False
        try:
            return _parse_datetime(expires_at) <= datetime.now(timezone.utc)
        except ValueError:
            return True


def merge_operation_results(*results: CacheOperationResult) -> CacheOperationResult:
    merged = CacheOperationResult()
    for result in results:
        merged.entries_deleted += result.entries_deleted
        merged.bytes_deleted += result.bytes_deleted
        merged.entries_scanned += result.entries_scanned
        merged.dry_run = merged.dry_run or result.dry_run
    return merged


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at_iso(ttl_seconds: int | None) -> str | None:
    if ttl_seconds is None:
        return None
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
