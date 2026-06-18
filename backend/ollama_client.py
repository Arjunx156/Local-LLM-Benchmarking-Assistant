"""
ollama_client.py — Async wrapper around the Ollama REST API.

All methods use a shared httpx.AsyncClient. Call `await client.health_check()`
before any other method to confirm Ollama is reachable.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional

import httpx

from backend.config import settings


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class ModelInfo:
    name: str
    size_bytes: int
    size_gb: float
    parameter_size: str
    quantization: str
    family: str
    modified_at: str

    @property
    def short_name(self) -> str:
        return self.name.split(":")[0]


@dataclass
class PullProgress:
    status: str
    digest: str = ""
    total: int = 0
    completed: int = 0

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return min(100.0, self.completed / self.total * 100)


@dataclass
class GenerateChunk:
    response: str = ""
    done: bool = False
    # Final-chunk fields (only populated when done=True)
    eval_count: int = 0
    eval_duration: int = 0          # nanoseconds
    prompt_eval_count: int = 0
    prompt_eval_duration: int = 0   # nanoseconds
    total_duration: int = 0         # nanoseconds
    load_duration: int = 0          # nanoseconds

    @property
    def tokens_per_second(self) -> float:
        if self.eval_duration == 0:
            return 0.0
        return self.eval_count / (self.eval_duration / 1e9)

    @property
    def total_time_sec(self) -> float:
        return self.total_duration / 1e9

    @property
    def ttft_sec(self) -> float:
        """Time to first token = load + prompt eval (rough approximation)."""
        return (self.load_duration + self.prompt_eval_duration) / 1e9


@dataclass
class ChatMessage:
    role: str   # "user" | "assistant" | "system"
    content: str


# ─── Client ───────────────────────────────────────────────────────────────────

class OllamaClient:
    """
    Thin async wrapper over Ollama's REST API.
    Re-uses a single AsyncClient for connection pooling.
    """

    def __init__(self, host: Optional[str] = None, timeout: float = 300.0):
        self.base_url = (host or settings.OLLAMA_HOST).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def aclose(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.aclose()

    # ── Health & version ──────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Return True if Ollama is running and reachable."""
        try:
            r = await self._client.get("/", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False

    async def get_version(self) -> str:
        """Return Ollama version string, e.g. '0.1.44'."""
        try:
            r = await self._client.get("/api/version")
            r.raise_for_status()
            return r.json().get("version", "unknown")
        except Exception:
            return "unknown"

    # ── Models ────────────────────────────────────────────────────────────────

    async def list_models(self) -> List[ModelInfo]:
        """Return all locally installed models."""
        r = await self._client.get("/api/tags")
        r.raise_for_status()
        raw = r.json().get("models", [])
        models: List[ModelInfo] = []
        for m in raw:
            details = m.get("details", {})
            size_bytes = m.get("size", 0)
            models.append(ModelInfo(
                name=m.get("name", ""),
                size_bytes=size_bytes,
                size_gb=round(size_bytes / 1024**3, 2),
                parameter_size=details.get("parameter_size", "?"),
                quantization=details.get("quantization_level", "?"),
                family=details.get("family", "?"),
                modified_at=m.get("modified_at", ""),
            ))
        return models

    async def pull_model(self, name: str) -> AsyncIterator[PullProgress]:
        """
        Stream pull progress for `name`.
        Yields PullProgress objects as the download advances.
        """
        payload = {"name": name, "stream": True}
        async with self._client.stream("POST", "/api/pull", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    yield PullProgress(
                        status=data.get("status", ""),
                        digest=data.get("digest", ""),
                        total=data.get("total", 0),
                        completed=data.get("completed", 0),
                    )
                except json.JSONDecodeError:
                    continue

    # ── Generation ────────────────────────────────────────────────────────────

    async def stream_generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        system: str = "",
    ) -> AsyncIterator[GenerateChunk]:
        """
        Stream a completion token by token.
        The last yielded chunk has done=True and contains all timing fields.
        """
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        async with self._client.stream("POST", "/api/generate", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    yield GenerateChunk(
                        response=data.get("response", ""),
                        done=data.get("done", False),
                        eval_count=data.get("eval_count", 0),
                        eval_duration=data.get("eval_duration", 0),
                        prompt_eval_count=data.get("prompt_eval_count", 0),
                        prompt_eval_duration=data.get("prompt_eval_duration", 0),
                        total_duration=data.get("total_duration", 0),
                        load_duration=data.get("load_duration", 0),
                    )
                except json.JSONDecodeError:
                    continue

    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        system: str = "",
    ) -> tuple[str, GenerateChunk]:
        """
        Non-streaming convenience wrapper.
        Returns (full_response_text, final_chunk_with_metrics).
        Also measures wall-clock TTFT by checking when the first token arrives.
        """
        full_text = ""
        final_chunk = GenerateChunk()
        first_token = True
        ttft_ns: int = 0
        t0 = time.monotonic_ns()

        async for chunk in self.stream_generate(
            model, prompt, temperature, top_p, max_tokens, system
        ):
            if first_token and chunk.response:
                ttft_ns = time.monotonic_ns() - t0
                first_token = False
            full_text += chunk.response
            if chunk.done:
                final_chunk = chunk
                # Inject wall-clock TTFT if Ollama didn't give load_duration
                if final_chunk.load_duration == 0:
                    final_chunk.load_duration = ttft_ns

        return full_text, final_chunk

    async def stream_chat(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ) -> AsyncIterator[GenerateChunk]:
        """Stream a chat completion (multi-turn)."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    msg = data.get("message", {})
                    yield GenerateChunk(
                        response=msg.get("content", ""),
                        done=data.get("done", False),
                        eval_count=data.get("eval_count", 0),
                        eval_duration=data.get("eval_duration", 0),
                        prompt_eval_count=data.get("prompt_eval_count", 0),
                        prompt_eval_duration=data.get("prompt_eval_duration", 0),
                        total_duration=data.get("total_duration", 0),
                        load_duration=data.get("load_duration", 0),
                    )
                except json.JSONDecodeError:
                    continue


# ─── Singleton ────────────────────────────────────────────────────────────────
# Import and use this instance everywhere instead of instantiating per-request.
ollama_client = OllamaClient()
