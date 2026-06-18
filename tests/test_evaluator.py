"""Tests for evaluator.py — all three evaluation strategies."""
import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, patch

from backend.evaluator import exact_match, code_execution, _extract_code, _normalise


class TestNormalise(unittest.TestCase):
    def test_lowercase(self):
        assert _normalise("PARIS") == "paris"

    def test_punctuation_removed(self):
        assert _normalise("Hello, World!") == "hello world"

    def test_word_to_number(self):
        assert _normalise("three") == "3"

    def test_extra_spaces(self):
        assert _normalise("  hello   world  ") == "hello world"


class TestExactMatch(unittest.TestCase):
    def test_perfect_match(self):
        assert exact_match("Paris", "paris") == 1.0

    def test_punctuation_tolerance(self):
        assert exact_match("The answer is 42.", "42") == 1.0

    def test_short_answer_in_long_response(self):
        assert exact_match("The capital of France is Paris, a beautiful city.", "paris") == 1.0

    def test_wrong_answer(self):
        assert exact_match("London", "paris") == 0.0

    def test_numeric_word(self):
        assert exact_match("three", "3") == 1.0

    def test_case_insensitive(self):
        assert exact_match("YES", "yes") == 1.0


class TestCodeExecution(unittest.TestCase):
    def test_correct_code(self):
        response = """Here is the solution:
```python
def fizzbuzz(n):
    if n % 15 == 0: return 'FizzBuzz'
    if n % 3 == 0: return 'Fizz'
    if n % 5 == 0: return 'Buzz'
    return str(n)
print(fizzbuzz(15))
```"""
        assert code_execution(response, "FizzBuzz") == 1.0

    def test_wrong_output(self):
        response = "```python\nprint('wrong')\n```"
        assert code_execution(response, "FizzBuzz") == 0.0

    def test_no_code_block(self):
        assert code_execution("No code here at all.", "FizzBuzz") == 0.0

    def test_syntax_error(self):
        response = "```python\ndef broken(\nprint(1)\n```"
        assert code_execution(response, "1") == 0.0

    def test_timeout(self):
        response = "```python\nwhile True: pass\n```"
        assert code_execution(response, "anything", timeout_sec=1) == 0.0

    def test_inline_code_fallback(self):
        response = "```python\nprint(42)\n```"
        assert code_execution(response, "42") == 1.0


class TestExtractCode(unittest.TestCase):
    def test_python_fence(self):
        resp = "Here:\n```python\nprint('hi')\n```\nDone."
        code = _extract_code(resp)
        assert code == "print('hi')"

    def test_plain_fence(self):
        resp = "```\nprint('hi')\n```"
        code = _extract_code(resp)
        assert code == "print('hi')"

    def test_no_fence_returns_none(self):
        assert _extract_code("just prose") is None

    def test_raw_def(self):
        resp = "def foo():\n    return 1\nprint(foo())"
        code = _extract_code(resp)
        assert code is not None


class TestLLMJudge(unittest.IsolatedAsyncioTestCase):
    async def test_valid_score(self):
        from backend.evaluator import llm_judge
        mock_text = '{"score": 8, "reason": "good answer"}'
        with patch("backend.ollama_client.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=(mock_text, None))
            score = await llm_judge("Q?", "expected", "actual")
        assert 0.0 <= score <= 1.0
        assert abs(score - 7/9) < 0.01   # (8-1)/9

    async def test_fallback_on_bad_json(self):
        from backend.evaluator import llm_judge
        with patch("backend.ollama_client.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=("not json at all!", None))
            score = await llm_judge("Q?", "expected", "actual")
        assert score == 0.5   # neutral fallback


if __name__ == "__main__":
    unittest.main()
