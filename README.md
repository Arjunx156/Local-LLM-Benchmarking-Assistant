# 🚀 Local LLM Benchmarking Assistant

> **Compare multiple local AI models side-by-side — 100% offline, no API keys required.**

Benchmarking is the process of measuring how well an AI model performs on a standardised set of tasks. It matters because raw parameter counts or marketing claims don't tell you how a model actually behaves on *your* machine with *your* hardware. This tool gives you objective, reproducible numbers — tokens per second, latency, accuracy scores — so you can make informed decisions about which model to use for coding, reasoning, summarisation, or general chat.

---

## ASCII Architecture

```
┌─────────────────────────────────────────────────┐
│                  User's Machine                 │
│                                                 │
│  ┌──────────────┐      ┌─────────────────────┐  │
│  │  Streamlit   │─────▶│   FastAPI Backend   │  │
│  │  Frontend    │      │   (port 8000)        │  │
│  │  (port 8501) │◀─────│                     │  │
│  └──────────────┘ HTTP │  ┌───────────────┐  │  │
│                         │  │ Benchmark     │  │  │
│                         │  │ Runner        │  │  │
│                         │  │ (asyncio)     │  │  │
│                         │  └──────┬────────┘  │  │
│                         └─────────│────────────┘  │
│                                   │ HTTP           │
│                         ┌─────────▼────────────┐  │
│                         │   Ollama Runtime     │  │
│                         │   (port 11434)        │  │
│                         │  llama3 / mistral /  │  │
│                         │  phi3 / tinyllama    │  │
│                         └──────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Install Ollama

| Platform | Command |
|----------|---------|
| **Windows** | Download from [ollama.com/download](https://ollama.com/download) and run the installer |
| **macOS** | `brew install ollama` |
| **Linux** | `curl -fsSL https://ollama.com/install.sh \| sh` |

### 2. Start Ollama and pull models

```bash
ollama serve                    # Start the Ollama server
ollama pull tinyllama           # Required — used as the LLM judge
ollama pull phi3                # Recommended lightweight model
ollama pull mistral             # Recommended general model
ollama pull llama3              # Optional — 8B parameter model
```

### 3. Install Python 3.11+

Download from [python.org](https://python.org) or use `pyenv`.

---

## Quick Start (3 commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the backend
uvicorn backend.main:app --reload --port 8000

# 3. Start the frontend (in a second terminal)
streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser.

---

## Docker Quick Start

```bash
# Ollama must already be running on the host
docker-compose up --build
```

Open **http://localhost:8501**.

---

## Benchmark Suites

| Suite | Questions | Eval Method | What it tests |
|-------|-----------|-------------|---------------|
| `reasoning` | 10 | exact_match + llm_judge | Logic, math puzzles, syllogisms |
| `coding` | 10 | code_execution | Code correctness via subprocess |
| `summarization` | 10 | llm_judge | Key point extraction quality |
| `factual` | 10 | exact_match | Factual recall accuracy |

### Adding Custom Questions

Add questions to any JSON file in `benchmark_suites/` using this format:

```json
{
  "id": "c011",
  "category": "coding",
  "difficulty": "medium",
  "prompt": "Write a Python function called `reverse_string` that reverses a string. Call reverse_string('hello') and print the result.",
  "expected_answer": "olleh",
  "evaluation_method": "code_execution"
}
```

**Evaluation methods:**
- `exact_match` — Normalised string comparison (case, punctuation, number words)
- `llm_judge` — Local LLM scores the answer 1–10 against the expected answer
- `code_execution` — Runs extracted Python code in a subprocess, compares stdout

---

## Sample Results

| Model | Score % | Tok/s | Latency (ms) | TTFT (ms) | Peak RAM (MB) |
|-------|---------|-------|-------------|-----------|---------------|
| mistral:7b | 74.2% | 18.4 | 3,241 | 412 | 5,120 |
| phi3:mini | 71.8% | 31.2 | 1,890 | 187 | 2,304 |
| llama3:8b | 69.5% | 14.1 | 4,120 | 631 | 6,144 |
| tinyllama | 42.3% | 58.7 | 890 | 98 | 768 |

*Results vary significantly by hardware. Measured on: Intel Core i7-12700K, 32GB RAM, NVIDIA RTX 3080.*

---

## Interpreting Results

**What does "12 tok/s" mean in practice?**

Tokens are roughly ¾ of a word. At 12 tok/s:
- A short reply (100 tokens) takes **~8 seconds**
- A paragraph (300 tokens) takes **~25 seconds**
- A long essay (1000 tokens) takes **~83 seconds**

For reference: a fast human reader reads at ~5 tok/s. Anything above 15 tok/s feels near-instant for short responses.

**Score %** ranges from 0–100%:
- `>75%` — Excellent. Model reliably answers correctly.
- `50–75%` — Good. Suitable for most tasks.
- `25–50%` — Fair. Model struggles with this category.
- `<25%` — Poor. Consider a larger model for this task type.

**TTFT (Time to First Token)** matters for interactive use. Under 500ms feels responsive; over 2 seconds feels sluggish.

---

## Configuration

Copy `.env.example` to `.env` and edit:

```env
OLLAMA_HOST=http://localhost:11434   # Change if Ollama is on another machine
JUDGE_MODEL=tinyllama                # Model used for llm_judge evaluation
MAX_CONCURRENT_QUESTIONS=3           # Lower if you have < 16GB RAM
CODE_EXEC_TIMEOUT_SEC=10             # Seconds before killing code subprocess
```

---

## Running Tests

```bash
pytest tests/ -v --asyncio-mode=auto
```

---

## Project Structure

```
local-llm-bench/
├── backend/
│   ├── main.py              # FastAPI — all 14 REST endpoints
│   ├── ollama_client.py     # Async Ollama API wrapper
│   ├── benchmark_runner.py  # asyncio orchestration (pause/resume/cancel)
│   ├── evaluator.py         # exact_match / llm_judge / code_execution
│   ├── job_store.py         # In-memory job registry + disk checkpointing
│   ├── metrics_collector.py # psutil CPU/RAM thread sampler
│   ├── report_generator.py  # Excel (openpyxl) + JSON report builder
│   └── config.py            # Pydantic Settings
├── frontend/
│   └── app.py               # Streamlit 5-tab dashboard
├── benchmark_suites/        # 40 hand-crafted benchmark questions
├── reports/                 # Auto-generated reports (gitignored)
├── tests/                   # pytest test suite
├── docker-compose.yml
└── requirements.txt
```
