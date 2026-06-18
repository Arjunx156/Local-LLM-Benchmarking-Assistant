"""Tests for ollama_client.py — health check, model listing, streaming."""
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOllamaClientHealth(unittest.IsolatedAsyncioTestCase):
    async def test_health_check_ok(self):
        from backend.ollama_client import OllamaClient
        client = OllamaClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            result = await client.health_check()
        assert result is True
        await client.aclose()

    async def test_health_check_fails_gracefully(self):
        from backend.ollama_client import OllamaClient
        client = OllamaClient()
        with patch.object(client._client, "get", side_effect=Exception("connection refused")):
            result = await client.health_check()
        assert result is False
        await client.aclose()

    async def test_get_version_unknown_on_error(self):
        from backend.ollama_client import OllamaClient
        client = OllamaClient()
        with patch.object(client._client, "get", side_effect=Exception("timeout")):
            v = await client.get_version()
        assert v == "unknown"
        await client.aclose()


class TestOllamaClientModels(unittest.IsolatedAsyncioTestCase):
    async def test_list_models_parses_response(self):
        from backend.ollama_client import OllamaClient
        payload = {
            "models": [
                {
                    "name": "llama3:latest",
                    "size": 4_661_224_676,
                    "modified_at": "2024-01-01T00:00:00Z",
                    "details": {
                        "family": "llama",
                        "parameter_size": "8B",
                        "quantization_level": "Q4_0",
                    },
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=payload)

        client = OllamaClient()
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            models = await client.list_models()

        assert len(models) == 1
        assert models[0].name == "llama3:latest"
        assert models[0].family == "llama"
        assert models[0].size_gb > 4.0
        await client.aclose()


class TestGenerateChunkMetrics(unittest.TestCase):
    def test_tokens_per_second(self):
        from backend.ollama_client import GenerateChunk
        chunk = GenerateChunk(
            done=True, eval_count=100, eval_duration=5_000_000_000
        )
        assert abs(chunk.tokens_per_second - 20.0) < 0.01

    def test_zero_duration(self):
        from backend.ollama_client import GenerateChunk
        chunk = GenerateChunk(done=True, eval_count=10, eval_duration=0)
        assert chunk.tokens_per_second == 0.0

    def test_total_time_sec(self):
        from backend.ollama_client import GenerateChunk
        chunk = GenerateChunk(done=True, total_duration=2_000_000_000)
        assert chunk.total_time_sec == 2.0


if __name__ == "__main__":
    unittest.main()
