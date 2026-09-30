"""Filesystem operations confined to generated job directories."""

import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from starlette.responses import FileResponse, JSONResponse
from starlette.types import Receive, Scope, Send


class MediaFiles:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir.resolve() / "media"
        self.root.mkdir(parents=True, exist_ok=True)
        self.readers: dict[str, int] = {}

    @contextmanager
    def hold(self, job_id: str) -> Iterator[None]:
        self.readers[job_id] = self.readers.get(job_id, 0) + 1
        try:
            yield
        finally:
            self.readers[job_id] -= 1
            if not self.readers[job_id]:
                del self.readers[job_id]

    def folder(self, job_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("Invalid job ID")
        path = self.root / job_id
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError("Unsafe job directory")
        return path

    def output(self, job_id: str, kind: str) -> Path:
        if kind not in {"mp4", "mp3"}:
            raise ValueError("Invalid media type")
        path = self.folder(job_id) / f"media.{kind}"
        if path.is_symlink() or not path.resolve().is_relative_to(self.folder(job_id)):
            raise ValueError("Unsafe output file")
        return path

    def remove(self, job_id: str) -> None:
        if self.readers.get(job_id):
            raise BlockingIOError("Media is being streamed")
        path = self.folder(job_id)
        if path.exists():
            shutil.rmtree(path)

    def size(self, job_id: str | None = None) -> int:
        root = self.folder(job_id) if job_id else self.root
        total = 0
        for path in root.rglob("*"):
            try:
                if not path.is_symlink() and path.is_file():
                    total += path.stat().st_size
            except FileNotFoundError:
                continue  # A worker may atomically rename a completed fragment.
        return total

    def clean_orphans(self, retained: set[str]) -> None:
        for path in self.root.iterdir():
            if re.fullmatch(r"[a-f0-9]{32}", path.name) and path.name not in retained:
                try:
                    if path.is_symlink():
                        path.unlink()
                    elif path.is_dir():
                        self.remove(path.name)
                except OSError:
                    continue  # Retry on the next maintenance pass, including on Windows.


class MediaResponse(FileResponse):
    """Keep an accepted transfer alive while expiry/removal denies new requests."""

    def __init__(self, files: MediaFiles, job_id: str, kind: str, name: str, inline: bool) -> None:
        self.files, self.job_id, self.kind = files, job_id, kind
        super().__init__(
            files.output(job_id, kind),
            filename=name,
            media_type="video/mp4" if kind == "mp4" else "audio/mpeg",
            content_disposition_type="inline" if inline else "attachment",
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        with self.files.hold(self.job_id):
            try:
                exists = self.files.output(self.job_id, self.kind).is_file()
            except ValueError:
                exists = False
            if not exists:
                await JSONResponse({"detail": "file_expired"}, status_code=410)(
                    scope, receive, send
                )
                return
            await super().__call__(scope, receive, send)
