"""Lock against opening the same ``.hestia`` file in two Hestia instances.

The lock is a sibling file ``<name>.hestia.lock`` created atomically (``O_EXCL``) with the
owner's pid, host and instance id. A lock left by a dead process on this host is stale and is
taken over silently; any other lock raises ``ProjectLockedError`` unless ``force`` is set.
"""

import contextlib
import getpass
import json
import os
import socket
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from hestia_project.errors import ProjectLockedError


class LockInfo(BaseModel):
    instance_id: str
    pid: int
    host: str
    user: str
    acquired_at: datetime


def lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":  # pragma: no cover - exercised on Windows only
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)  # type: ignore[reportUnknownMemberType]
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(code))  # type: ignore[reportUnknownMemberType]
            return code.value == still_active
        finally:
            kernel32.CloseHandle(handle)  # type: ignore[reportUnknownMemberType]
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_lock(path: Path) -> LockInfo | None:
    try:
        return LockInfo.model_validate_json(lock_path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@dataclass
class ProjectLock:
    path: Path
    instance_id: str

    def release(self) -> None:
        """Remove the lock file if it is still ours."""
        info = read_lock(self.path)
        if info is None or info.instance_id == self.instance_id:
            with contextlib.suppress(OSError):
                lock_path(self.path).unlink()


def acquire_lock(path: Path, instance_id: str, force: bool = False) -> ProjectLock:
    target = lock_path(path)
    info = LockInfo(
        instance_id=instance_id,
        pid=os.getpid(),
        host=socket.gethostname(),
        user=getpass.getuser(),
        acquired_at=datetime.now(UTC),
    )
    for _ in range(2):
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            holder = read_lock(path)
            stale = holder is None or (holder.host == info.host and not _pid_alive(holder.pid))
            if holder is not None and holder.instance_id == instance_id:
                stale = True  # our own lock (e.g. reopening the same file)
            if not (stale or force):
                assert holder is not None
                raise ProjectLockedError(
                    f"{path.name} está abierto en otra instancia de Hestia "
                    f"({holder.user}@{holder.host}, pid {holder.pid}).",
                    path=str(path),
                    holder=holder.model_dump(mode="json"),
                ) from None
            with contextlib.suppress(FileNotFoundError):
                target.unlink()
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(info.model_dump(mode="json")))
        return ProjectLock(path=path, instance_id=instance_id)
    raise ProjectLockedError(f"No se pudo bloquear {path.name}.", path=str(path))
