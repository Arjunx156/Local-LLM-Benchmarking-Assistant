"""
benchmark_runner.py — Async benchmark orchestration engine.

Flow per job:
  for model in job.models:           # SEQUENTIAL — one model at a time
    for question in suite.questions: # CONCURRENT — up to MAX_CONCURRENT_QUESTIONS
      await pause_event.wait()
      if cancel_flag: break
      collect metrics → call Ollama → evaluate → store result → checkpoint
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from backend.config import settings
from backend.evaluator import evaluate
from backend.job_store import BenchmarkJob, JobStatus, QuestionResult, job_store
from backend.metrics_collector import MetricsCollector
from backend.ollama_client import ollama_client


# ─── Benchmark suite loader ───────────────────────────────────────────────────

@dataclass
class BenchmarkQuestion:
    id: str
    category: str
    difficulty: str
    prompt: str
    expected_answer: str
    evaluation_method: str   # exact_match | llm_judge | code_execution


def load_suite(suite_name: str) -> List[BenchmarkQuestion]:
    """
    Load a benchmark suite JSON file.
    `suite_name` should be the base name without extension, e.g. 'reasoning'.
    """
    path = settings.BENCHMARK_SUITES_DIR / f"{suite_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Benchmark suite not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        BenchmarkQuestion(
            id=q["id"],
            category=q["category"],
            difficulty=q["difficulty"],
            prompt=q["prompt"],
            expected_answer=q["expected_answer"],
            evaluation_method=q["evaluation_method"],
        )
        for q in raw
    ]


def list_suites() -> List[str]:
    """Return the names of all available benchmark suites."""
    suite_dir = settings.BENCHMARK_SUITES_DIR
    if not suite_dir.exists():
        return []
    return [p.stem for p in sorted(suite_dir.glob("*.json"))]


# ─── Core runner ──────────────────────────────────────────────────────────────

async def run_benchmark_job(job_id: str) -> None:
    """
    Entry point — launched as an asyncio Task by the FastAPI endpoint.
    All state mutations go through job_store for thread-safety.
    """
    job = job_store.get(job_id)
    if job is None:
        return

    # Ensure the asyncio.Event is created in the correct event loop
    if job._pause_event is None:
        job._pause_event = asyncio.Event()
        job._pause_event.set()

    job_store.update_status(job_id, "running")

    try:
        suite_questions = load_suite(job.suite)
    except FileNotFoundError as exc:
        job_store.update_status(job_id, "error", str(exc))
        return

    job_store.update_progress(
        job_id,
        total_questions_per_model=len(suite_questions),
        total_models=len(job.models),
    )

    for model_idx, model in enumerate(job.models):
        # Re-check cancellation between models
        if job.is_cancelled:
            break

        job_store.update_progress(
            job_id,
            current_model=model,
            models_done=model_idx,
            current_question_idx=0,
        )

        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_QUESTIONS)

        async def run_one_question(
            q: BenchmarkQuestion, q_idx: int, _model: str = model
        ) -> None:
            """Coroutine for a single question — guards pause/cancel."""
            async with semaphore:
                # ── Pause gate ────────────────────────────────────────────────
                job_store.update_status(job_id, "paused" if not job._pause_event.is_set() else "running")
                await job.wait_if_paused()

                # ── Cancel gate ───────────────────────────────────────────────
                if job.is_cancelled:
                    return

                job_store.update_progress(
                    job_id,
                    current_question_idx=q_idx,
                    current_tokens_per_second=0.0,
                )

                # ── Metrics + generation ──────────────────────────────────────
                collector = MetricsCollector(poll_interval=0.5)
                collector.start()

                t_wall_start = time.monotonic()
                response_text = ""
                ttft_ms = 0.0
                tok_per_sec = 0.0
                tokens_generated = 0
                total_time_ms = 0.0
                error_msg: Optional[str] = None

                try:
                    first_token = True
                    async for chunk in ollama_client.stream_generate(
                        model=_model,
                        prompt=q.prompt,
                        temperature=0.7,
                        max_tokens=1024,
                    ):
                        if first_token and chunk.response:
                            ttft_ms = (time.monotonic() - t_wall_start) * 1000
                            first_token = False

                        response_text += chunk.response

                        if chunk.done:
                            tokens_generated = chunk.eval_count
                            tok_per_sec = chunk.tokens_per_second
                            total_time_ms = chunk.total_time_sec * 1000

                        # Broadcast live tok/s
                        if tok_per_sec > 0:
                            job_store.update_progress(
                                job_id,
                                current_tokens_per_second=tok_per_sec,
                            )

                    if total_time_ms == 0:
                        total_time_ms = (time.monotonic() - t_wall_start) * 1000

                except Exception as exc:
                    error_msg = str(exc)
                    total_time_ms = (time.monotonic() - t_wall_start) * 1000

                metrics = collector.stop()

                # ── Evaluation ────────────────────────────────────────────────
                score = 0.0
                if not error_msg:
                    try:
                        score = await evaluate(
                            question_text=q.prompt,
                            expected_answer=q.expected_answer,
                            model_response=response_text,
                            evaluation_method=q.evaluation_method,
                        )
                    except Exception as exc:
                        error_msg = f"Eval error: {exc}"

                # ── Store ─────────────────────────────────────────────────────
                result = QuestionResult(
                    question_id=q.id,
                    category=q.category,
                    difficulty=q.difficulty,
                    prompt=q.prompt,
                    expected_answer=q.expected_answer,
                    evaluation_method=q.evaluation_method,
                    model=_model,
                    response_text=response_text,
                    score=score,
                    ttft_ms=round(ttft_ms, 2),
                    total_time_ms=round(total_time_ms, 2),
                    tokens_generated=tokens_generated,
                    tokens_per_second=round(tok_per_sec, 2),
                    peak_ram_mb=round(metrics.get("peak_ram_mb", 0.0), 1),
                    peak_vram_mb=round(metrics.get("peak_vram_mb", 0.0), 1),
                    avg_cpu_percent=round(metrics.get("avg_cpu_percent", 0.0), 1),
                    error=error_msg,
                )
                job_store.add_result(job_id, result)
                job_store.save_to_disk(job_id)

        # Run all questions for this model concurrently (bounded by semaphore)
        tasks = [
            asyncio.create_task(run_one_question(q, idx))
            for idx, q in enumerate(suite_questions, start=1)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        if job.is_cancelled:
            break

        job_store.update_progress(job_id, models_done=model_idx + 1)

    # ── Finalise ──────────────────────────────────────────────────────────────
    if job.is_cancelled:
        job_store.update_status(job_id, "cancelled")
    else:
        job_store.update_status(job_id, "done")

    job_store.save_to_disk(job_id)
