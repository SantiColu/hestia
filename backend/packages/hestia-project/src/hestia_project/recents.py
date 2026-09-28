"""Recently opened projects, stored per user in ``<hestia home>/recents.json``."""

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from hestia_project.base import Schema

MAX_RECENTS = 12


class RecentEntry(Schema):
    path: str
    name: str
    opened_at: datetime


class RecentProject(RecentEntry):
    exists: bool
    """False when the file was moved or deleted since it was last opened."""


_entries = TypeAdapter(list[RecentEntry])


class RecentProjects:
    def __init__(self, file: Path) -> None:
        self.file = file

    def _load(self) -> list[RecentEntry]:
        try:
            return _entries.validate_json(self.file.read_bytes())
        except (OSError, ValidationError):
            return []

    def _store(self, entries: list[RecentEntry]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([e.model_dump(mode="json") for e in entries], indent=2), encoding="utf-8"
        )
        with contextlib.suppress(OSError):
            tmp.replace(self.file)

    def list(self) -> list[RecentProject]:
        return [
            RecentProject(**entry.model_dump(), exists=Path(entry.path).is_file())
            for entry in self._load()
        ]

    def touch(self, path: Path, name: str) -> None:
        key = str(path.resolve())
        entries = [e for e in self._load() if e.path != key]
        entries.insert(0, RecentEntry(path=key, name=name, opened_at=datetime.now(UTC)))
        self._store(entries[:MAX_RECENTS])

    def remove(self, path: str) -> bool:
        keys = {path, str(Path(path).resolve())}
        entries = self._load()
        kept = [e for e in entries if e.path not in keys]
        if len(kept) == len(entries):
            return False
        self._store(kept)
        return True
