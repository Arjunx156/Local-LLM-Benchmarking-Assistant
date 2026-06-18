"""
config.py — Centralised settings via pydantic-settings.
All values can be overridden with environment variables or a .env file.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ollama
    OLLAMA_HOST: str = "http://localhost:11434"
    # Which local model acts as the LLM judge for qualitative scoring.
    # tinyllama is tiny/fast; change to phi3 or mistral for better judgement.
    JUDGE_MODEL: str = "tinyllama"

    # Benchmark runner
    # Max questions to run concurrently PER MODEL (keeps RAM sane)
    MAX_CONCURRENT_QUESTIONS: int = 3
    # Seconds before we kill a subprocess running model-generated code
    CODE_EXEC_TIMEOUT_SEC: int = 10

    # Paths (relative to project root where uvicorn / streamlit are launched)
    REPORTS_DIR: Path = Path("reports")
    BENCHMARK_SUITES_DIR: Path = Path("benchmark_suites")

    # FastAPI
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Streamlit calls the backend at this URL
    BACKEND_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Ensure output dirs exist at import time
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
