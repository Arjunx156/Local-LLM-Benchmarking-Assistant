"""
evaluator.py — Three evaluation strategies for benchmark question scoring.

  exact_match    — normalise + compare strings; handles numbers/punctuation
  llm_judge      — ask a local LLM to score the answer 1-10
  code_execution — extract Python from model response, run in subprocess
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from typing import Optional

from backend.config import settings


# ─── Normalisation helpers ────────────────────────────────────────────────────

_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")

# Common word-to-number mappings (avoids word2number import for robustness)
_WORD_NUMS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90", "hundred": "100",
}


def _normalise(text: str) -> str:
    """Lower-case, remove punctuation, collapse whitespace, map number words."""
    text = text.lower().strip()
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    words = text.split()
    words = [_WORD_NUMS.get(w, w) for w in words]
    return " ".join(words)


# ─── Exact match ──────────────────────────────────────────────────────────────

def exact_match(response: str, expected: str) -> float:
    """
    Returns 1.0 if the normalised response matches the normalised expected,
    0.0 otherwise.  Leading/trailing prose is tolerated when expected is short
    (≤ 5 words) and appears anywhere inside the response.
    """
    norm_resp = _normalise(response)
    norm_exp = _normalise(expected)

    # Direct match
    if norm_resp == norm_exp:
        return 1.0

    # If expected is a short answer, allow it to appear inside a longer response
    if len(norm_exp.split()) <= 5 and norm_exp in norm_resp:
        return 1.0

    return 0.0


# ─── LLM judge ────────────────────────────────────────────────────────────────

_JUDGE_SYSTEM = (
    "You are a strict, impartial answer evaluator. "
    "You ONLY respond with a single valid JSON object and nothing else."
)

_JUDGE_PROMPT_TEMPLATE = """\
Evaluate the quality of the following model answer compared to the expected answer.

Question: {question}

Expected answer: {expected}

Model answer: {response}

Score the model answer on a scale of 1 to 10:
- 10: Perfectly correct and complete
- 7-9: Mostly correct with minor omissions or phrasing differences
- 4-6: Partially correct, captures some key ideas
- 1-3: Mostly wrong or irrelevant

Respond with ONLY this JSON (no prose, no markdown fences):
{{"score": <integer 1-10>, "reason": "<one short sentence>"}}
"""


async def llm_judge(
    question: str,
    expected: str,
    response: str,
    judge_model: Optional[str] = None,
) -> float:
    """
    Use a local LLM to score the response.
    Returns normalised score in [0.0, 1.0].
    Falls back to 0.5 on any failure.
    """
    # Import here to avoid circular at module level
    from backend.ollama_client import ollama_client

    model = judge_model or settings.JUDGE_MODEL
    prompt = _JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        expected=expected,
        response=response[:2000],  # truncate very long answers
    )

    for attempt in range(3):
        try:
            text, _ = await ollama_client.generate(
                model=model,
                prompt=prompt,
                system=_JUDGE_SYSTEM,
                temperature=0.0,   # deterministic scoring
                max_tokens=128,
            )
            # Extract JSON — the model sometimes wraps it in fences
            json_match = re.search(r'\{.*?\}', text, re.DOTALL)
            if not json_match:
                continue
            data = json.loads(json_match.group())
            raw_score = int(data.get("score", 5))
            raw_score = max(1, min(10, raw_score))
            return round((raw_score - 1) / 9, 3)   # map [1,10] → [0,1]
        except Exception:
            await asyncio.sleep(0.5 * (attempt + 1))

    return 0.5   # neutral fallback


# ─── Code execution ───────────────────────────────────────────────────────────

_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def _extract_code(response: str) -> Optional[str]:
    """
    Extract Python code from a model response.
    Tries markdown fences first, then the whole response as a fallback.
    """
    fences = _CODE_FENCE_RE.findall(response)
    if fences:
        # Return the largest code block (most likely to be the full solution)
        return max(fences, key=len).strip()

    # If no fence found, check if the whole response looks like code
    stripped = response.strip()
    if stripped.startswith(("def ", "import ", "class ", "#")):
        return stripped

    return None


def code_execution(
    response: str,
    expected_output: str,
    timeout_sec: Optional[int] = None,
) -> float:
    """
    Extract Python code from response, run it in a subprocess, compare stdout.
    Returns 1.0 on exact match, 0.0 otherwise.
    Never raises — all errors are caught and scored 0.0.
    """
    timeout = timeout_sec or settings.CODE_EXEC_TIMEOUT_SEC
    code = _extract_code(response)
    if not code:
        return 0.0

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        actual = result.stdout.strip()
        expected = expected_output.strip()
        if actual == expected:
            return 1.0
        # Try normalised compare for numeric outputs
        if _normalise(actual) == _normalise(expected):
            return 1.0
        return 0.0
    except subprocess.TimeoutExpired:
        return 0.0
    except Exception:
        return 0.0


# ─── Dispatcher ───────────────────────────────────────────────────────────────

async def evaluate(
    question_text: str,
    expected_answer: str,
    model_response: str,
    evaluation_method: str,
    judge_model: Optional[str] = None,
) -> float:
    """
    Route to the correct evaluation function and return a score in [0.0, 1.0].
    """
    method = evaluation_method.lower()

    if method == "exact_match":
        return exact_match(model_response, expected_answer)

    elif method == "llm_judge":
        return await llm_judge(
            question=question_text,
            expected=expected_answer,
            response=model_response,
            judge_model=judge_model,
        )

    elif method == "code_execution":
        # Run in executor so we don't block the event loop during subprocess.run
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            code_execution,
            model_response,
            expected_answer,
            settings.CODE_EXEC_TIMEOUT_SEC,
        )

    else:
        # Unknown method — default to partial credit
        return 0.5
