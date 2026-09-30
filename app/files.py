"""Filesystem operations confined to generated job directories."""

import re
import shutil
from pathlib import Path


class MediaFiles:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir.resolve() / "media"
        self.root.mkdir(parents=True, exist_ok=True)

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
                if path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    self.remove(path.name)
