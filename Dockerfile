# Use Python 3.12 slim image
FROM python:3.12-slim

# Install system dependencies
# git is often needed for installing dependencies from git repos
# curl is needed to install uv
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock requirements.txt ./
COPY src/ src/
COPY launcher.py .
COPY run.sh .

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv sync --frozen --all-extras

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Pre-download the ChromaDB embedding model to prevent unexpected downloads at runtime
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()(['init'])"

# Run the launcher
CMD ["python", "launcher.py"]
