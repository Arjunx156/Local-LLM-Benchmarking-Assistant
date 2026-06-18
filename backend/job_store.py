"""
job_store.py — In-memory job registry with disk checkpointing.

Each BenchmarkJob lives in RAM for fast access. After every question result is
added the job is snapshotted to <REPORTS_DIR>/<job_id>/job.json so it survives
backend restarts.
"""
from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from backend.config import settings


# ─── Sub-models ───────────────────────────────────────────────────────────────

@dataclass
class QuestionResult:
    question_id: str
    category: str
    difficulty: str
    prompt: str
    expected_answer: str
    evaluation_method: str
    model: str
    response_text: str
    score: float                  # 0.0 – 1.0
    ttft_ms: float                # time to first token (ms)
    total_time_ms: float          # wall-clock total (ms)
    tokens_generated: int
    tokens_per_second: float
    peak_ram_mb: float
    peak_vram_mb: float = 0.0
    avg_cpu_percent: float
    error: Optional[str] = None   # populated if the call failed


@dataclass
class JobProgress:
    current_model: str = ""
    current_question_idx: int = 0
    total_questions_per_model: int = 0
    models_done: int = 0
    total_models: int = 0
    current_tokens_per_second: float = 0.0

    @property
    def overall_percent(self) -> float:
        total = self.total_models * self.total_questions_per_model
        if total == 0:
            return 0.0
        done = self.models_done * self.total_questions_per_model + self.current_question_idx
        return min(100.0, done / total * 100)


JobStatus = Literal["queued", "running", "paused", "done", "cancelled", "error"]


@dataclass
class BenchmarkJob:
    job_id: str
    models: List[str]
    suite: str
    status: JobStatus = "queued"
    results: List[QuestionResult] = field(default_factory=list)
    progress: JobProgress = field(default_factory=JobProgress)
    error_message: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    # ── Runtime-only (not persisted) ──────────────────────────────────────────
    # asyncio.Event — set=running, clear=paused
    _pause_event: Any = field(default=None, compare=False, repr=False)
    _cancel_flag: bool = field(default=False, compare=False, repr=False)

    def __post_init__(self):
        if self._pause_event is None:
            try:
                self._pause_event = asyncio.Event()
                self._pause_event.set()   # start in running state
            except RuntimeError:
                # No event loop yet (happens in tests); set lazily in runner
                self._pause_event = None

    # ── Pause / Resume / Cancel helpers ───────────────────────────────────────

    def pause(self):
        if self._pause_event:
            self._pause_event.clear()

    def resume(self):
        if self._pause_event:
            self._pause_event.set()

    def cancel(self):
        self._cancel_flag = True
        self.resume()   # unblock any waiting coroutines

    async def wait_if_paused(self):
        """Await this inside the runner before each question."""
        if self._pause_event:
            await self._pause_event.wait()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_flag


# ─── Store ────────────────────────────────────────────────────────────────────

class JobStore:
    """
    Thread-safe in-memory store for BenchmarkJob objects.
    Uses a reentrant lock so the async runner (via run_in_executor or
    asyncio.create_task) and the FastAPI request handlers can both access it
    safely.
    """

    def __init__(self):
        self._jobs: Dict[str, BenchmarkJob] = {}
        self._lock = threading.RLock()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, models: List[str], suite: str) -> BenchmarkJob:
        job = BenchmarkJob(
            job_id=str(uuid.uuid4()),
            models=models,
            suite=suite,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[BenchmarkJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_all(self) -> List[BenchmarkJob]:
        with self._lock:
            return list(self._jobs.values())

    def update_status(self, job_id: str, status: JobStatus, error: str = "") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                if error:
                    job.error_message = error
                if status in ("done", "cancelled", "error"):
                    job.completed_at = datetime.now(timezone.utc).isoformat()

    def add_result(self, job_id: str, result: QuestionResult) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.results.append(result)

    def update_progress(self, job_id: str, **kwargs) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                for k, v in kwargs.items():
                    if hasattr(job.progress, k):
                        setattr(job.progress, k, v)

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_to_disk(self, job_id: str) -> None:
        """Serialise the job (without asyncio fields) to JSON."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            data = _serialise_job(job)

        job_dir = settings.REPORTS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "job.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass  # Non-fatal — don't crash the runner

    def load_from_disk(self, job_id: str) -> Optional[BenchmarkJob]:
        """Restore a job snapshot. Useful after backend restart."""
        path = settings.REPORTS_DIR / job_id / "job.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            job = _deserialise_job(data)
            with self._lock:
                self._jobs[job_id] = job
            return job
        except Exception:
            return None


# ─── Serialisation helpers ────────────────────────────────────────────────────

def _serialise_job(job: BenchmarkJob) -> dict:
    """Convert a BenchmarkJob to a plain dict (strips asyncio fields)."""
    return {
        "job_id": job.job_id,
        "models": job.models,
        "suite": job.suite,
        "status": job.status,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "progress": {
            "current_model": job.progress.current_model,
            "current_question_idx": job.progress.current_question_idx,
            "total_questions_per_model": job.progress.total_questions_per_model,
            "models_done": job.progress.models_done,
            "total_models": job.progress.total_models,
            "current_tokens_per_second": job.progress.current_tokens_per_second,
        },
        "results": [asdict(r) for r in job.results],
    }


def _deserialise_job(data: dict) -> BenchmarkJob:
    results = [QuestionResult(**r) for r in data.get("results", [])]
    prog_data = data.get("progress", {})
    progress = JobProgress(
        current_model=prog_data.get("current_model", ""),
        current_question_idx=prog_data.get("current_question_idx", 0),
        total_questions_per_model=prog_data.get("total_questions_per_model", 0),
        models_done=prog_data.get("models_done", 0),
        total_models=prog_data.get("total_models", 0),
        current_tokens_per_second=prog_data.get("current_tokens_per_second", 0.0),
    )
    return BenchmarkJob(
        job_id=data["job_id"],
        models=data.get("models", []),
        suite=data.get("suite", ""),
        status=data.get("status", "done"),
        results=results,
        progress=progress,
        error_message=data.get("error_message"),
        created_at=data.get("created_at", ""),
        completed_at=data.get("completed_at"),
    )


def job_to_dict(job: BenchmarkJob) -> dict:
    """Public serialisation used by FastAPI responses."""
    return _serialise_job(job)


# ─── Singleton ────────────────────────────────────────────────────────────────
job_store = JobStore()
