# Makefile for py-github-analyzer development

.PHONY: help install install-dev test test-unit test-integration test-e2e test-performance
.PHONY: lint format type-check security docs clean build publish
.PHONY: coverage coverage-html coverage-report
.PHONY: docker-build docker-test docker-run
.PHONY: benchmark profile

# Default target
help:
	@echo "py-github-analyzer Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install package in development mode"
	@echo "  install-dev      Install with development dependencies"
	@echo "  install-all      Install with all optional dependencies"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test             Run all tests (unit + integration)"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"  
	@echo "  test-e2e         Run end-to-end tests"
	@echo "  test-performance Run performance tests"
	@echo "  test-all         Run all test suites"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint             Run all linters"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run mypy type checking"
	@echo "  security         Run security scans"
	@echo ""
	@echo "Coverage Commands:"
	@echo "  coverage         Generate coverage report"
	@echo "  coverage-html    Generate HTML coverage report"
	@echo "  coverage-report  Open coverage report in browser"
	@echo ""
	@echo "Documentation Commands:"
	@echo "  docs             Build documentation"
	@echo "  docs-serve       Build and serve documentation"
	@echo ""
	@echo "Build Commands:"
	@echo "  clean            Clean build artifacts"
	@echo "  build            Build package"
	@echo "  publish          Publish to PyPI (requires credentials)"
	@echo ""
	@echo "Performance Commands:"
	@echo "  benchmark        Run performance benchmarks"
	@echo "  profile          Run memory profiling"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-test      Run tests in Docker container"
	@echo "  docker-run       Run application in Docker container"

# Setup Commands
install:
	pip install -e .

install-dev:
	pip install -e .[dev]

install-all:
	pip install -e .[all]

# Testing Commands
test:
	pytest tests/unit tests/integration -v

test-unit:
	pytest tests/unit -v --tb=short

test-integration:
	pytest tests/integration -v --tb=short

test-e2e:
	pytest tests/e2e -v --tb=short -x

test-performance:
	pytest tests/performance -v --tb=short -k "not slow"

test-performance-full:
	pytest tests/performance -v --tb=short

test-all:
	pytest tests/ -v

test-parallel:
	pytest tests/unit tests/integration -v -n auto

# Code Quality Commands
lint:
	@echo "Running Black..."
	black --check --diff py_github_analyzer tests
	@echo "Running isort..."
	isort --check-only --diff py_github_analyzer tests  
	@echo "Running flake8..."
	flake8 py_github_analyzer tests

format:
	@echo "Formatting with Black..."
	black py_github_analyzer tests
	@echo "Sorting imports with isort..."
	isort py_github_analyzer tests

type-check:
	@echo "Running mypy type checking..."
	mypy py_github_analyzer

security:
	@echo "Running bandit security scan..."
	bandit -r py_github_analyzer
	@echo "Running safety check..."
	safety check

# Coverage Commands
coverage:
	pytest tests/unit tests/integration --cov=py_github_analyzer --cov-report=term-missing --cov-report=html

coverage-html:
	pytest tests/unit tests/integration --cov=py_github_analyzer --cov-report=html
	@echo "Coverage report generated in htmlcov/"

coverage-report: coverage-html
	@python -c "import webbrowser; webbrowser.open('htmlcov/index.html')"

# Documentation Commands
docs:
	sphinx-build -W -b html docs docs/_build/html

docs-serve:
	sphinx-build -W -b html docs docs/_build/html
	@echo "Starting documentation server at http://localhost:8000"
	cd docs/_build/html && python -m http.server 8000

# Build Commands
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .tox/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean
	@echo "Building package..."
	python -m build

publish: build
	@echo "Publishing to PyPI..."
	twine upload dist/*

publish-test: build
	@echo "Publishing to Test PyPI..."
	twine upload --repository testpypi dist/*

# Performance Commands
benchmark:
	@echo "Running performance benchmarks..."
	pytest tests/performance -v --tb=short -k "benchmark"

profile:
	@echo "Running memory profiling..."
	pytest tests/performance -v --tb=short -k "memory" --profile

# Docker Commands  
docker-build:
	docker build -t py-github-analyzer:latest .

docker-test:
	docker run --rm py-github-analyzer:latest pytest tests/unit tests/integration -v

docker-run:
	docker run --rm -it py-github-analyzer:latest

# Development helpers
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything is working."

quick-test:
	pytest tests/unit -v --tb=line -x

watch-tests:
	@echo "Watching for changes... (Press Ctrl+C to stop)"
	@while true; do \
		find py_github_analyzer tests -name "*.py" | entr -d make quick-test; \
	done

# CI simulation
ci-local:
	@echo "Running full CI pipeline locally..."
	make clean
	make lint
	make type-check  
	make security
	make test-all
	make coverage
	make docs
	make build
	@echo "Local CI pipeline completed successfully!"

# Release helpers
version:
	@python -c "import py_github_analyzer; print(f'Current version: {py_github_analyzer.__version__}')"

pre-release: ci-local
	@echo "Pre-release checks completed successfully!"
	@echo "Ready for release. Don't forget to:"
	@echo "1. Update CHANGELOG.md"
	@echo "2. Create and push git tag"
	@echo "3. GitHub Actions will handle the release"

# Database of common development tasks
common-issues:
	@echo "Common Development Issues and Solutions:"
	@echo "======================================="
	@echo ""
	@echo "Import errors:"
	@echo "  Solution: make install-dev"
	@echo ""
	@echo "Test failures:"
	@echo "  Solution: make test-unit (run unit tests first)"
	@echo ""
	@echo "Type check errors:"
	@echo "  Solution: make type-check"
	@echo ""
	@echo "Code formatting issues:"
	@echo "  Solution: make format"
	@echo ""
	@echo "Coverage too low:"
	@echo "  Solution: make coverage-html (see detailed report)"
