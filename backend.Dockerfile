FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (needed for compilation if necessary)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir sqlalchemy pynvml

# Copy application code
COPY backend ./backend
COPY benchmark_suites ./benchmark_suites

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
