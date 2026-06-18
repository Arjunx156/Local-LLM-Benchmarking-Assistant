"""Tests for benchmark_runner.py — job lifecycle, pause/resume, cancellation."""
import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.job_store import JobStore, QuestionResult


class TestJobStore(unittest.TestCase):
    def setUp(self):
        self.store = JobStore()

    def test_create_returns_job(self):
        job = self.store.create(["llama3"], "reasoning")
        assert job.job_id
        assert job.models == ["llama3"]
        assert job.suite == "reasoning"
        assert job.status == "queued"

    def test_get_nonexistent(self):
        assert self.store.get("nonexistent") is None

    def test_update_status(self):
        job = self.store.create(["llama3"], "factual")
        self.store.update_status(job.job_id, "running")
        assert self.store.get(job.job_id).status == "running"

    def test_add_result(self):
        job = self.store.create(["llama3"], "factual")
        result = QuestionResult(
            question_id="f001", category="factual", difficulty="easy",
            prompt="What is 2+2?", expected_answer="4",
            evaluation_method="exact_match", model="llama3",
            response_text="4", score=1.0, ttft_ms=50.0,
            total_time_ms=200.0, tokens_generated=5,
            tokens_per_second=25.0, peak_ram_mb=1024.0, avg_cpu_percent=30.0,
        )
        self.store.add_result(job.job_id, result)
        updated = self.store.get(job.job_id)
        assert len(updated.results) == 1
        assert updated.results[0].score == 1.0

    def test_pause_resume(self):
        job = self.store.create(["llama3"], "factual")
        # pause_event starts set (running)
        assert job._pause_event is None or job._pause_event.is_set()
        job._pause_event = asyncio.Event()
        job._pause_event.set()
        job.pause()
        assert not job._pause_event.is_set()
        job.resume()
        assert job._pause_event.is_set()

    def test_cancel_flag(self):
        job = self.store.create(["llama3"], "factual")
        assert not job.is_cancelled
        job.cancel()
        assert job.is_cancelled

    def test_get_all(self):
        self.store.create(["llama3"], "reasoning")
        self.store.create(["mistral"], "coding")
        assert len(self.store.get_all()) == 2


class TestBenchmarkRunnerLoader(unittest.TestCase):
    def test_list_suites_returns_list(self):
        from backend.benchmark_runner import list_suites
        # Should not raise even if directory is missing
        suites = list_suites()
        assert isinstance(suites, list)

    def test_load_suite_file_not_found(self):
        from backend.benchmark_runner import load_suite
        with self.assertRaises(FileNotFoundError):
            load_suite("nonexistent_suite_xyz")


class TestBenchmarkRunnerAsync(unittest.IsolatedAsyncioTestCase):
    async def test_job_reaches_done_status(self):
        from backend.benchmark_runner import run_benchmark_job
        from backend.job_store import job_store

        job = job_store.create(["tinyllama"], "factual")

        # Mock the Ollama stream to return a fake response
        async def fake_stream(*args, **kwargs):
            from backend.ollama_client import GenerateChunk
            yield GenerateChunk(response="paris", done=False)
            yield GenerateChunk(
                response="", done=True,
                eval_count=5, eval_duration=500_000_000,
                total_duration=600_000_000,
            )

        with patch("backend.benchmark_runner.ollama_client.stream_generate", side_effect=fake_stream):
            with patch("backend.benchmark_runner.load_suite") as mock_load:
                from backend.benchmark_runner import BenchmarkQuestion
                mock_load.return_value = [
                    BenchmarkQuestion(
                        id="f001", category="factual", difficulty="easy",
                        prompt="Capital of France?", expected_answer="paris",
                        evaluation_method="exact_match",
                    )
                ]
                await run_benchmark_job(job.job_id)

        final = job_store.get(job.job_id)
        assert final.status == "done"
        assert len(final.results) == 1
        assert final.results[0].score == 1.0


if __name__ == "__main__":
    unittest.main()
