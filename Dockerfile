# Multi-stage Dockerfile for py-github-analyzer
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Development stage
FROM base as development

# Copy requirements first for better caching
COPY pyproject.toml ./
COPY setup.py ./
COPY README.md ./

# Install package in development mode
RUN pip install -e .[dev]

# Copy source code
COPY . .

# Run tests by default
CMD ["pytest", "tests/unit", "tests/integration", "-v"]

# Production stage
FROM base as production

# Copy and install package
COPY pyproject.toml ./
COPY setup.py ./
COPY README.md ./
COPY py_github_analyzer/ ./py_github_analyzer/

# Install package
RUN pip install .

# Create non-root user
RUN useradd --create-home --shell /bin/bash analyzer
USER analyzer

# Set entrypoint
ENTRYPOINT ["py-github-analyzer"]
CMD ["--help"]

# Testing stage
FROM development as testing

# Copy test files
COPY tests/ ./tests/

# Run comprehensive tests
CMD ["pytest", "tests/", "-v", "--cov=py_github_analyzer"]
