You are an expert AI engineer. Build a fully production-ready Local LLM Benchmarking 
Assistant from scratch. This system runs AI models 100% locally (no cloud APIs required) 
and produces a professional benchmark report comparing multiple models.

=== TECH STACK ===
- Runtime: Ollama (models run locally)
- Backend: Python 3.11, FastAPI
- Frontend: Streamlit
- Data: pandas, plotly (charts), openpyxl (Excel export)
- System metrics: psutil (RAM/CPU monitoring)
- Async: asyncio, httpx
- Deployment: Docker + docker-compose (Ollama runs separately)

=== FOLDER STRUCTURE ===
local-llm-bench/
├── backend/
│   ├── main.py               # FastAPI
│   ├── ollama_client.py      # All Ollama API calls
│   ├── benchmark_runner.py   # Core benchmarking logic
│   ├── metrics_collector.py  # CPU/RAM tracking
│   ├── report_generator.py   # Excel + PDF report generation
│   └── config.py
├── frontend/
│   └── app.py                # Streamlit dashboard
├── benchmark_suites/
│   ├── reasoning.json        # Test questions for reasoning
│   ├── coding.json           # Test questions for code generation
│   ├── summarization.json    # Test questions for summarization
│   └── factual.json          # Test questions for factual recall
├── reports/                  # Generated reports saved here
├── tests/
│   └── test_benchmark_runner.py
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md

=== FEATURES TO BUILD ===

1. MODEL MANAGEMENT
   - On startup, call Ollama API to list all locally installed models
   - Show available models in UI with their sizes (in GB)
   - Button to pull a new model by name (show download progress via streaming)
   - Models to support out of the box: llama3, mistral, phi3, gemma, codellama, tinyllama
   - Detect if Ollama is not running and show a friendly setup guide

2. BENCHMARK SUITES
   Create 4 JSON benchmark files, each with 10 questions + correct answers:
   
   reasoning.json — logic puzzles, multi-step math word problems
   coding.json — "write a Python function that does X", evaluated by running the code
   summarization.json — long text + expected key points to extract
   factual.json — factual questions with known correct short answers
   
   Each question object format:
   {
     "id": "r001",
     "category": "reasoning",
     "difficulty": "medium",
     "prompt": "...",
     "expected_answer": "...",
     "evaluation_method": "llm_judge" | "exact_match" | "code_execution"
   }

3. BENCHMARK RUNNER
   - Run selected benchmark suite against selected models (multi-select)
   - For each model × question:
     * Record: time_to_first_token_ms, total_response_time_ms, tokens_generated,
       tokens_per_second, peak_ram_mb, avg_cpu_percent, response_text
   - Evaluation methods:
     * exact_match: strip + lowercase compare
     * llm_judge: send (question, expected, actual) to a judge model, ask for 1-10 score
     * code_execution: extract Python code block, run it in subprocess with timeout=10s,
       check if output matches expected
   - Run questions concurrently (asyncio) but one model at a time to avoid OOM
   - Show live progress: "Model llama3 | Question 4/10 | 12.3 tok/s"
   - Allow pause/resume/cancel

4. METRICS COLLECTION
   - Before each query: record baseline RAM
   - During query: poll CPU every 500ms using psutil
   - After query: record peak RAM delta (model overhead)
   - Calculate tokens/second from Ollama's eval_count and eval_duration fields

5. RESULTS DASHBOARD
   - Summary table: model name | avg score | avg tok/s | avg latency | avg RAM
   - Bar chart: tokens/second per model (plotly)
   - Radar chart: model scores across 4 categories (reasoning, coding, etc.)
   - Line chart: latency vs difficulty (easy/medium/hard)
   - Heatmap: model × category score matrix
   - All charts must be interactive (plotly, not matplotlib)

6. DETAILED RESULTS VIEW
   - Click any row in summary table → see question-by-question breakdown
   - Show side-by-side: expected answer vs model answer
   - Color code: green (pass), red (fail), yellow (partial)
   - Show raw response time distribution as histogram

7. REPORT GENERATION
   - Export to Excel: one sheet per model, summary sheet, charts embedded
   - Export to JSON: full raw results for reproducibility
   - Report includes: system specs (CPU model, RAM, OS), Ollama version,
     model versions, benchmark suite version, timestamp, all raw metrics

8. CHAT PLAYGROUND
   - After benchmarks, switch to a "Playground" tab
   - Select any local model, set temperature/top_p/max_tokens sliders
   - Chat interface with streaming responses
   - Show live tokens/second counter while model is responding
   - Compare mode: send same message to 2 models simultaneously, show side by side

9. SYSTEM REQUIREMENTS CHECKER
   - On startup, check: available RAM, available disk space, Ollama installation
   - For each available model, show: "Your system can run this ✅" or "Needs Xgb RAM ❌"

10. FASTAPI ENDPOINTS
    - GET /models — list available Ollama models
    - POST /models/pull — pull a model (streaming progress)
    - POST /benchmark/run — start a benchmark job, returns job_id
    - GET /benchmark/{job_id}/status — poll job status + live results
    - GET /benchmark/{job_id}/results — full results when done
    - POST /chat — single chat completion with metrics
    - GET /system — system specs

=== README MUST INCLUDE ===
- What benchmarking means and why it matters (1 paragraph)
- ASCII architecture diagram
- Prerequisites: Ollama installation instructions (Mac/Windows/Linux)
- Quick start: 3 commands to run everything
- How to add custom benchmark questions (JSON format)
- Sample benchmark results table (with fake but realistic numbers)
- Interpretation guide: what does "12 tok/s" mean in practice?

=== OUTPUT ===
Write every file completely. Every benchmark JSON must have exactly 10 real, 
well-crafted questions with correct answers. All charts must use plotly with 
consistent color scheme (use a professional palette, not default colors).
The full project must run with: pip install -r requirements.txt && 
streamlit run frontend/app.py