"""
job_store.py — Supabase-backed job registry.

Each BenchmarkJob is persisted in a Supabase PostgreSQL database.
Local execution state (pause/cancel) is held in memory for now.
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from supabase import create_client, Client

from backend.config import settings

# ─── Supabase Client ──────────────────────────────────────────────────────────

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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

# ─── Runtime State ────────────────────────────────────────────────────────────

@dataclass
class RuntimeJobState:
    pause_event: Optional[asyncio.Event] = None
    cancel_flag: bool = False

    def __post_init__(self):
        if self.pause_event is None:
            try:
                self.pause_event = asyncio.Event()
                self.pause_event.set()
            except RuntimeError:
                self.pause_event = None

# ─── Store ────────────────────────────────────────────────────────────────────

class JobStore:
    """
    Supabase-backed store for BenchmarkJob objects.
    Maintains a local dict of RuntimeJobStates to manage pause/cancel events
    for jobs actively running in the current process.
    """

    def __init__(self):
        self._runtime_states: Dict[str, RuntimeJobState] = {}
        self._lock = threading.RLock()

    def _get_runtime_state(self, job_id: str) -> RuntimeJobState:
        with self._lock:
            if job_id not in self._runtime_states:
                self._runtime_states[job_id] = RuntimeJobState()
            return self._runtime_states[job_id]

    def create(self, models: List[str], suite: str) -> BenchmarkJob:
        job_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        # Insert into Supabase
        data = {
            "job_id": job_id,
            "models": models,
            "suite": suite,
            "status": "queued",
            "progress": asdict(JobProgress()),
            "created_at": created_at,
        }
        supabase.table("benchmark_jobs").insert(data).execute()
        
        # Initialize runtime state locally
        self._get_runtime_state(job_id)
        
        return BenchmarkJob(
            job_id=job_id,
            models=models,
            suite=suite,
            created_at=created_at
        )

    def get(self, job_id: str) -> Optional[BenchmarkJob]:
        # Fetch job from Supabase
        response = supabase.table("benchmark_jobs").select("*").eq("job_id", job_id).execute()
        if not response.data:
            return None
        job_data = response.data[0]
        
        # Fetch results
        results_response = supabase.table("question_results").select("*").eq("job_id", job_id).execute()
        results = [QuestionResult(**{k: v for k, v in r.items() if k != 'id' and k != 'job_id'}) for r in results_response.data]
        
        prog_data = job_data.get("progress", {})
        progress = JobProgress(**prog_data)
        
        return BenchmarkJob(
            job_id=job_data["job_id"],
            models=job_data.get("models", []),
            suite=job_data.get("suite", ""),
            status=job_data.get("status", "done"),
            results=results,
            progress=progress,
            error_message=job_data.get("error_message"),
            created_at=job_data.get("created_at", ""),
            completed_at=job_data.get("completed_at"),
        )

    def get_all(self) -> List[BenchmarkJob]:
        response = supabase.table("benchmark_jobs").select("*").order("created_at", desc=True).execute()
        jobs = []
        for job_data in response.data:
            job_id = job_data["job_id"]
            results_response = supabase.table("question_results").select("*").eq("job_id", job_id).execute()
            results = [QuestionResult(**{k: v for k, v in r.items() if k != 'id' and k != 'job_id'}) for r in results_response.data]
            
            prog_data = job_data.get("progress", {})
            progress = JobProgress(**prog_data)
            
            jobs.append(BenchmarkJob(
                job_id=job_data["job_id"],
                models=job_data.get("models", []),
                suite=job_data.get("suite", ""),
                status=job_data.get("status", "done"),
                results=results,
                progress=progress,
                error_message=job_data.get("error_message"),
                created_at=job_data.get("created_at", ""),
                completed_at=job_data.get("completed_at"),
            ))
        return jobs

    def update_status(self, job_id: str, status: JobStatus, error: str = "") -> None:
        update_data = {"status": status}
        if error:
            update_data["error_message"] = error
        if status in ("done", "cancelled", "error"):
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            
        supabase.table("benchmark_jobs").update(update_data).eq("job_id", job_id).execute()

    def add_result(self, job_id: str, result: QuestionResult) -> None:
        data = asdict(result)
        data["job_id"] = job_id
        supabase.table("question_results").insert(data).execute()

    def update_progress(self, job_id: str, **kwargs) -> None:
        # We need to fetch the current progress, update it, and save it
        response = supabase.table("benchmark_jobs").select("progress").eq("job_id", job_id).execute()
        if not response.data:
            return
            
        prog_data = response.data[0].get("progress", {})
        for k, v in kwargs.items():
            prog_data[k] = v
            
        supabase.table("benchmark_jobs").update({"progress": prog_data}).eq("job_id", job_id).execute()

    def save_to_disk(self, job_id: str) -> None:
        # No-op since we write to DB directly
        pass

    def load_from_disk(self, job_id: str) -> Optional[BenchmarkJob]:
        # Legacy compat, just map to get
        return self.get(job_id)

    # ── Pause / Resume / Cancel logic (Local to the running process) ────────
    
    def pause(self, job_id: str):
        state = self._get_runtime_state(job_id)
        if state.pause_event:
            state.pause_event.clear()
        self.update_status(job_id, "paused")

    def resume(self, job_id: str):
        state = self._get_runtime_state(job_id)
        if state.pause_event:
            state.pause_event.set()
        self.update_status(job_id, "running")

    def cancel(self, job_id: str):
        state = self._get_runtime_state(job_id)
        state.cancel_flag = True
        if state.pause_event:
            state.pause_event.set() # Unblock

    async def wait_if_paused(self, job_id: str):
        state = self._get_runtime_state(job_id)
        # Handle case where event loop wasn't ready during __post_init__
        if state.pause_event is None:
            state.pause_event = asyncio.Event()
            state.pause_event.set()
            # If job in DB is already paused, we should clear it
            job = self.get(job_id)
            if job and job.status == "paused":
                state.pause_event.clear()
                
        await state.pause_event.wait()

    def is_cancelled(self, job_id: str) -> bool:
        state = self._get_runtime_state(job_id)
        return state.cancel_flag

# ─── Serialisation helpers (Public API for FastAPI) ──────────────────────────

def job_to_dict(job: BenchmarkJob) -> dict:
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
            "overall_percent": job.progress.overall_percent,
        },
        "results": [asdict(r) for r in job.results],
    }

# ─── Singleton ────────────────────────────────────────────────────────────────
job_store = JobStore()
