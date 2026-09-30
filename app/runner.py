import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

from filelock import FileLock

from app.config import Settings
from app.files import MediaFiles
from app.store import Store

logger = logging.getLogger(__name__)


class JobFailure(Exception):
    pass


class Runner:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.files = MediaFiles(settings.data_dir)
        self.task: asyncio.Task[None] | None = None
        self.current_task: asyncio.Task[None] | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.active_id: str | None = None
        self.lock = FileLock(settings.data_dir / "runner.lock", thread_local=False)

    async def start(self) -> None:
        self.lock.acquire(timeout=0)
        try:
            self.store.recover()
            for job_id in self.store.expire():
                self.files.remove(job_id)
            self.files.clean_orphans(self.store.retained_ids())
            self.task = asyncio.create_task(self._loop())
        except BaseException:
            self.lock.release()
            raise

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        self.lock.release()

    async def cancel(self, job_id: str) -> None:
        self.store.update(job_id, state="cancelled")
        if self.active_id == job_id and self.current_task:
            self.current_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.current_task
        self.files.remove(job_id)

    def command(self, job: dict[str, Any]) -> list[str]:
        args = [
            sys.executable,
            "-m",
            "app.worker",
            "--url",
            job["url"],
            "--kind",
            job["kind"],
            "--quality",
            str(job["quality"]),
            "--max-duration",
            str(self.settings.max_duration_seconds),
            "--max-file-bytes",
            str(self.settings.max_file_bytes),
            "--js-runtime",
            self.settings.js_runtime,
        ]
        if self.settings.ffmpeg_location:
            args.extend(["--ffmpeg-location", self.settings.ffmpeg_location])
        return args

    async def _loop(self) -> None:
        while True:
            try:
                for job_id in self.store.expire():
                    self.files.remove(job_id)
                job = self.store.claim()
                if job:
                    self.active_id = job["id"]
                    self.current_task = asyncio.create_task(self._execute(job))
                    try:
                        await asyncio.shield(self.current_task)
                    except asyncio.CancelledError:
                        # A user cancellation ends only this job; service shutdown ends the loop.
                        loop_task = asyncio.current_task()
                        if loop_task and loop_task.cancelling():
                            self.current_task.cancel()
                            with contextlib.suppress(asyncio.CancelledError):
                                await self.current_task
                            raise
                    finally:
                        self.active_id = None
                        self.current_task = None
                else:
                    await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Queue maintenance failed")
                await asyncio.sleep(1)

    async def _terminate(self) -> None:
        process = self.process
        if not process or process.returncode is not None:
            return
        if os.name == "nt":
            killer = await asyncio.create_subprocess_exec(
                "taskkill",
                "/PID",
                str(process.pid),
                "/T",
                "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await killer.wait()
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        with contextlib.suppress(ProcessLookupError):
            if process.returncode is None:
                process.kill()
        await process.wait()

    async def _consume(self, job_id: str) -> str | None:
        assert self.process and self.process.stdout
        error = None
        last_progress = 0.0
        while line := await self.process.stdout.readline():
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(event, dict):
                continue
            if event.get("event") == "metadata":
                self.store.update(job_id, title=str(event.get("title", ""))[:300])
            elif event.get("event") == "progress" and time.monotonic() - last_progress > 0.4:
                value = event.get("percent", 0)
                if isinstance(value, (int, float)):
                    self.store.update(job_id, progress=max(0, min(99, value)))
                    last_progress = time.monotonic()
            elif event.get("event") == "processing":
                self.store.update(job_id, state="processing", progress=99)
            elif event.get("event") == "error":
                candidate = event.get("code")
                error = (
                    candidate
                    if candidate in {"duration_limit", "live_unsupported", "size_limit"}
                    else "provider_error"
                )
        return error

    async def _execute(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        reader: asyncio.Task[str | None] | None = None
        succeeded = False
        failure: str | None = None
        output_size = 0
        try:
            if self.files.size() + self.settings.max_job_bytes > self.settings.max_storage_bytes:
                raise JobFailure("storage_full")
            self.files.folder(job_id).mkdir()
            env = {
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
                "PYTHONUTF8": "1",
            }
            spawn = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *self.command(job),
                    cwd=self.files.folder(job_id),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    start_new_session=os.name != "nt",
                    limit=65536,
                )
            )
            try:
                self.process = await asyncio.shield(spawn)
            except asyncio.CancelledError:
                self.process = await spawn
                raise
            reader = asyncio.create_task(self._consume(job_id))
            deadline = time.monotonic() + self.settings.job_timeout_seconds
            while self.process.returncode is None:
                if time.monotonic() > deadline:
                    raise JobFailure("timeout")
                if self.files.size(job_id) > self.settings.max_job_bytes:
                    raise JobFailure("size_limit")
                if self.files.size() > self.settings.max_storage_bytes:
                    raise JobFailure("storage_full")
                if reader.done() and reader.exception():
                    raise JobFailure("provider_error")
                await asyncio.sleep(0.2)
            error = await reader
            if self.process.returncode or error:
                raise JobFailure(error or "provider_error")
            output = self.files.output(job_id, job["kind"])
            if not output.is_file() or output.stat().st_size == 0:
                raise JobFailure("provider_error")
            if output.stat().st_size > self.settings.max_file_bytes:
                raise JobFailure("size_limit")
            output_size = output.stat().st_size
            succeeded = True
        except asyncio.CancelledError:
            failure = "interrupted"
            raise
        except JobFailure as exc:
            failure = str(exc)
        except Exception:
            logger.exception("Job %s failed", job_id)
            failure = "processing_error"
        finally:
            await self._terminate()
            self.process = None
            if reader:
                if not reader.done():
                    reader.cancel()
                with contextlib.suppress(asyncio.CancelledError, ValueError):
                    await reader
            if not succeeded:
                self.files.remove(job_id)
                self.store.update(job_id, state="failed", error=failure or "processing_error")
            else:
                self.store.update(job_id, state="complete", progress=100, file_bytes=output_size)
