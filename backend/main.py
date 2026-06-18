"""
main.py — FastAPI application. All REST endpoints + SSE streaming.
Run with: uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import platform
from typing import List, Optional

import psutil
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.benchmark_runner import list_suites, run_benchmark_job
from backend.config import settings
from backend.job_store import job_store, job_to_dict
from backend.metrics_collector import get_system_info
from backend.ollama_client import ChatMessage, ollama_client
from backend.report_generator import generate_excel_report, generate_json_report

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LLM Bench API",
    description="Local LLM benchmarking backend — 100% local, no cloud APIs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response models ────────────────────────────────────────────────

class BenchmarkRunRequest(BaseModel):
    models: List[str]
    suite: str


class PullModelRequest(BaseModel):
    name: str


class ChatRequest(BaseModel):
    model: str
    messages: List[dict]           # [{role, content}, ...]
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    stream: bool = False


# ─── Models ───────────────────────────────────────────────────────────────────

@app.get("/models", tags=["Models"])
async def list_models():
    """List all locally installed Ollama models with sizes."""
    is_up = await ollama_client.health_check()
    if not is_up:
        raise HTTPException(503, "Ollama is not running. Start with: ollama serve")

    models = await ollama_client.list_models()
    sys_ram_gb = psutil.virtual_memory().total / 1024**3

    result = []
    for m in models:
        # Rough model RAM heuristic: size_gb * 1.15 headroom factor
        needed_gb = round(m.size_gb * 1.15, 1)
        can_run = sys_ram_gb >= needed_gb
        result.append({
            "name": m.name,
            "size_gb": m.size_gb,
            "parameter_size": m.parameter_size,
            "quantization": m.quantization,
            "family": m.family,
            "modified_at": m.modified_at,
            "can_run": can_run,
            "ram_needed_gb": needed_gb,
        })
    return {"models": result, "ollama_running": True}


@app.post("/models/pull", tags=["Models"])
async def pull_model(req: PullModelRequest):
    """Stream pull progress for a model as Server-Sent Events."""
    async def event_gen():
        try:
            async for progress in ollama_client.pull_model(req.name):
                yield {
                    "data": json.dumps({
                        "status": progress.status,
                        "digest": progress.digest,
                        "total": progress.total,
                        "completed": progress.completed,
                        "percent": round(progress.percent, 1),
                    })
                }
        except Exception as exc:
            yield {"data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_gen())


# ─── Benchmark ────────────────────────────────────────────────────────────────

@app.get("/suites", tags=["Benchmark"])
async def get_suites():
    """Return available benchmark suite names."""
    return {"suites": list_suites()}


@app.post("/benchmark/run", tags=["Benchmark"])
async def start_benchmark(req: BenchmarkRunRequest):
    """Create a benchmark job and launch it as an async background task."""
    if not req.models:
        raise HTTPException(400, "Provide at least one model name.")
    if not req.suite:
        raise HTTPException(400, "Provide a suite name.")

    is_up = await ollama_client.health_check()
    if not is_up:
        raise HTTPException(503, "Ollama is not running.")

    job = job_store.create(models=req.models, suite=req.suite)

    # Schedule the runner as a background asyncio Task — returns immediately
    asyncio.create_task(run_benchmark_job(job.job_id))

    return {"job_id": job.job_id, "status": "queued"}


@app.get("/benchmark/{job_id}/status", tags=["Benchmark"])
async def stream_job_status(job_id: str):
    """
    SSE endpoint — streams live job progress every 500ms.
    The stream ends when the job reaches a terminal state.
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(404, f"Job {job_id} not found.")

    async def event_gen():
        terminal = {"done", "cancelled", "error"}
        while True:
            j = job_store.get(job_id)
            if j is None:
                break
            yield {"data": json.dumps(job_to_dict(j))}
            if j.status in terminal:
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_gen())


@app.get("/benchmark/{job_id}/poll", tags=["Benchmark"])
async def poll_job_status(job_id: str):
    """Non-SSE status endpoint for simple polling (used by Streamlit)."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(404, f"Job {job_id} not found.")
    return job_to_dict(job)


@app.post("/benchmark/{job_id}/pause", tags=["Benchmark"])
async def pause_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status != "running":
        raise HTTPException(400, f"Job is {job.status}, not running.")
    job.pause()
    job_store.update_status(job_id, "paused")
    return {"status": "paused"}


@app.post("/benchmark/{job_id}/resume", tags=["Benchmark"])
async def resume_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status != "paused":
        raise HTTPException(400, f"Job is {job.status}, not paused.")
    job.resume()
    job_store.update_status(job_id, "running")
    return {"status": "running"}


@app.post("/benchmark/{job_id}/cancel", tags=["Benchmark"])
async def cancel_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status in ("done", "cancelled", "error"):
        raise HTTPException(400, f"Job is already {job.status}.")
    job.cancel()
    return {"status": "cancelling"}


@app.get("/benchmark/{job_id}/results", tags=["Benchmark"])
async def get_results(job_id: str):
    """Return full results JSON for a completed job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job_to_dict(job)


@app.get("/benchmark/history", tags=["Benchmark"])
async def job_history():
    """Return summary of all past jobs (including completed)."""
    jobs = job_store.get_all()
    return [
        {
            "job_id": j.job_id,
            "models": j.models,
            "suite": j.suite,
            "status": j.status,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
            "result_count": len(j.results),
        }
        for j in jobs
    ]


# ─── Reports ──────────────────────────────────────────────────────────────────

@app.get("/reports/{job_id}/excel", tags=["Reports"])
async def download_excel(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status != "done":
        raise HTTPException(400, "Job is not complete yet.")
    path = generate_excel_report(job)
    return FileResponse(
        path=str(path),
        filename=f"llm_bench_{job_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/reports/{job_id}/json", tags=["Reports"])
async def download_json(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    path = generate_json_report(job)
    return FileResponse(
        path=str(path),
        filename=f"llm_bench_{job_id[:8]}.json",
        media_type="application/json",
    )


# ─── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/chat", tags=["Chat"])
async def chat(req: ChatRequest):
    """Single chat completion. Streams if req.stream=True."""
    is_up = await ollama_client.health_check()
    if not is_up:
        raise HTTPException(503, "Ollama is not running.")

    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in req.messages]

    if req.stream:
        async def stream_gen():
            async for chunk in ollama_client.stream_chat(
                model=req.model,
                messages=messages,
                temperature=req.temperature,
                top_p=req.top_p,
                max_tokens=req.max_tokens,
            ):
                yield json.dumps({
                    "delta": chunk.response,
                    "done": chunk.done,
                    "tokens_per_second": round(chunk.tokens_per_second, 2) if chunk.done else 0,
                    "eval_count": chunk.eval_count,
                }) + "\n"

        return StreamingResponse(stream_gen(), media_type="application/x-ndjson")

    # Non-streaming
    full = ""
    final_chunk = None
    async for chunk in ollama_client.stream_chat(
        model=req.model,
        messages=messages,
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
    ):
        full += chunk.response
        if chunk.done:
            final_chunk = chunk

    return {
        "response": full,
        "model": req.model,
        "tokens_per_second": round(final_chunk.tokens_per_second, 2) if final_chunk else 0,
        "eval_count": final_chunk.eval_count if final_chunk else 0,
        "total_duration_sec": round(final_chunk.total_time_sec, 3) if final_chunk else 0,
    }


# ─── System ───────────────────────────────────────────────────────────────────

@app.get("/system", tags=["System"])
async def system_info():
    """Return hardware specs + Ollama version + installed models summary."""
    info = get_system_info()
    ollama_running = await ollama_client.health_check()
    ollama_version = await ollama_client.get_version() if ollama_running else "N/A"
    model_count = 0
    if ollama_running:
        try:
            models = await ollama_client.list_models()
            model_count = len(models)
        except Exception:
            pass

    return {
        **info,
        "ollama_running": ollama_running,
        "ollama_version": ollama_version,
        "installed_model_count": model_count,
    }


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "ollama": await ollama_client.health_check()}
