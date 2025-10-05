# py-github-analyzer Development Makefile
# High-performance async GitHub repository analyzer
# Author: Han Jun-hee <createbrain2heart@gmail.com>

# ==================================================
# Variables
# ==================================================

PYTHON := python
PIP := pip
PACKAGE_NAME := py_github_analyzer
TEST_DIR := tests
DIST_DIR := dist
BUILD_DIR := build

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color
BOLD := \033[1m

# ==================================================
# Help
# ==================================================

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "$(BOLD)py-github-analyzer Development Commands$(NC)"
	@echo "======================================"
	@echo ""
	@echo "$(BOLD)Setup Commands:$(NC)"
	@echo "  install          Install package in production mode"
	@echo "  install-dev      Install package in development mode with all dependencies"
	@echo "  install-test     Install package with test dependencies only"
	@echo "  dev-setup        Complete development environment setup"
	@echo ""
	@echo "$(BOLD)Testing Commands:$(NC)"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run only unit tests"
	@echo "  test-integration Run only integration tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-watch       Run tests in watch mode (requires pytest-xdist)"
	@echo "  test-parallel    Run tests in parallel"
	@echo ""
	@echo "$(BOLD)Code Quality Commands:$(NC)"
	@echo "  lint             Run all linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  format-check     Check code formatting without making changes"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-check   Run security checks with bandit and safety"
	@echo "  quality          Run all code quality checks"
	@echo "  quality-fix      Run all code quality fixes (format + lint)"
	@echo ""
	@echo "$(BOLD)Build and Release Commands:$(NC)"
	@echo "  clean            Clean build artifacts and cache files"
	@echo "  build            Build package for distribution"
	@echo "  build-check      Check built package integrity"
	@echo "  upload-test      Upload to TestPyPI"
	@echo "  upload           Upload to PyPI"
	@echo "  release          Full release process (clean + build + upload)"
	@echo ""
	@echo "$(BOLD)Development Commands:$(NC)"
	@echo "  run-example      Run example analysis on a test repository"
	@echo "  profile          Profile the application performance"
	@echo "  docs             Generate and serve documentation"
	@echo "  update-deps      Update all dependencies"
	@echo "  freeze-deps      Freeze current dependencies to requirements.txt"
	@echo ""
	@echo "$(BOLD)CI/CD Commands:$(NC)"
	@echo "  ci               Run complete CI pipeline locally"
	@echo "  pre-commit       Install pre-commit hooks"
	@echo "  validate         Validate package configuration and dependencies"
	@echo ""

# ==================================================
# Setup Commands
# ==================================================

.PHONY: install
install: ## Install package in production mode
	@echo "$(GREEN)📦 Installing py-github-analyzer...$(NC)"
	$(PIP) install .
	@echo "$(GREEN)✅ Installation complete!$(NC)"

.PHONY: install-dev
install-dev: ## Install package in development mode with all dependencies
	@echo "$(GREEN)🔧 Installing development environment...$(NC)"
	$(PIP) install -e .[dev]
	@echo "$(GREEN)✅ Development installation complete!$(NC)"

.PHONY: install-test
install-test: ## Install package with test dependencies only
	@echo "$(GREEN)🧪 Installing test dependencies...$(NC)"
	$(PIP) install -e .[test]
	@echo "$(GREEN)✅ Test installation complete!$(NC)"

.PHONY: dev-setup
dev-setup: install-dev pre-commit ## Complete development environment setup
	@echo "$(GREEN)🚀 Development environment setup complete!$(NC)"
	@echo "$(YELLOW)💡 You can now run 'make test' to verify everything is working$(NC)"

# ==================================================
# Testing Commands
# ==================================================

.PHONY: test
test: ## Run all tests
	@echo "$(GREEN)🧪 Running all tests...$(NC)"
	pytest $(TEST_DIR) -v
	@echo "$(GREEN)✅ All tests passed!$(NC)"

.PHONY: test-unit
test-unit: ## Run only unit tests
	@echo "$(GREEN)⚡ Running unit tests...$(NC)"
	pytest $(TEST_DIR) -v -m "unit"
	@echo "$(GREEN)✅ Unit tests passed!$(NC)"

.PHONY: test-integration
test-integration: ## Run only integration tests
	@echo "$(GREEN)🔗 Running integration tests...$(NC)"
	pytest $(TEST_DIR) -v -m "integration"
	@echo "$(GREEN)✅ Integration tests passed!$(NC)"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "$(GREEN)📊 Running tests with coverage...$(NC)"
	pytest $(TEST_DIR) --cov=$(PACKAGE_NAME) --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✅ Coverage report generated in htmlcov/$(NC)"

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@echo "$(GREEN)👀 Running tests in watch mode...$(NC)"
	pytest $(TEST_DIR) --cov=$(PACKAGE_NAME) -f
	@echo "$(YELLOW)Press Ctrl+C to stop watching$(NC)"

.PHONY: test-parallel
test-parallel: ## Run tests in parallel
	@echo "$(GREEN)⚡ Running tests in parallel...$(NC)"
	pytest $(TEST_DIR) -v -n auto
	@echo "$(GREEN)✅ Parallel tests completed!$(NC)"

# ==================================================
# Code Quality Commands
# ==================================================

.PHONY: format
format: ## Format code with black and isort
	@echo "$(GREEN)🎨 Formatting code...$(NC)"
	black $(PACKAGE_NAME) $(TEST_DIR)
	isort $(PACKAGE_NAME) $(TEST_DIR)
	@echo "$(GREEN)✅ Code formatted!$(NC)"

.PHONY: format-check
format-check: ## Check code formatting without making changes
	@echo "$(GREEN)🔍 Checking code formatting...$(NC)"
	black --check $(PACKAGE_NAME) $(TEST_DIR)
	isort --check-only $(PACKAGE_NAME) $(TEST_DIR)
	@echo "$(GREEN)✅ Code formatting is correct!$(NC)"

.PHONY: lint
lint: ## Run flake8 linting
	@echo "$(GREEN)🔍 Running linting checks...$(NC)"
	flake8 $(PACKAGE_NAME) $(TEST_DIR)
	@echo "$(GREEN)✅ Linting passed!$(NC)"

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "$(GREEN)🔍 Running type checks...$(NC)"
	mypy $(PACKAGE_NAME)
	@echo "$(GREEN)✅ Type checking passed!$(NC)"

.PHONY: security-check
security-check: ## Run security checks with bandit and safety
	@echo "$(GREEN)🔒 Running security checks...$(NC)"
	bandit -r $(PACKAGE_NAME) -f json -o bandit-report.json || true
	safety check --json --output safety-report.json || true
	@echo "$(GREEN)✅ Security checks completed! Check *-report.json files$(NC)"

.PHONY: quality
quality: format-check lint type-check ## Run all code quality checks
	@echo "$(GREEN)✨ All quality checks passed!$(NC)"

.PHONY: quality-fix
quality-fix: format lint ## Run all code quality fixes
	@echo "$(GREEN)🛠️ Code quality fixes applied!$(NC)"

# ==================================================
# Build and Release Commands
# ==================================================

.PHONY: clean
clean: ## Clean build artifacts and cache files
	@echo "$(GREEN)🧹 Cleaning build artifacts...$(NC)"
	rm -rf $(BUILD_DIR)/
	rm -rf $(DIST_DIR)/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf bandit-report.json
	rm -rf safety-report.json
	rm -rf profile.stats
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "$(GREEN)✅ Cleanup complete!$(NC)"

.PHONY: build
build: clean ## Build package for distribution
	@echo "$(GREEN)📦 Building package...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✅ Package built successfully!$(NC)"
	@echo "$(YELLOW)📄 Built files:$(NC)"
	@ls -la $(DIST_DIR)/

.PHONY: build-check
build-check: build ## Check built package integrity
	@echo "$(GREEN)🔍 Checking package integrity...$(NC)"
	twine check $(DIST_DIR)/*
	@echo "$(GREEN)✅ Package integrity verified!$(NC)"

.PHONY: upload-test
upload-test: build-check ## Upload to TestPyPI
	@echo "$(YELLOW)⚠️ Uploading to TestPyPI...$(NC)"
	twine upload --repository testpypi $(DIST_DIR)/*
	@echo "$(GREEN)✅ Uploaded to TestPyPI!$(NC)"

.PHONY: upload
upload: build-check ## Upload to PyPI
	@echo "$(RED)⚠️ PRODUCTION UPLOAD: Are you sure? Press Ctrl+C to cancel, Enter to continue$(NC)"
	@read
	@echo "$(YELLOW)📤 Uploading to PyPI...$(NC)"
	twine upload $(DIST_DIR)/*
	@echo "$(GREEN)🎉 Successfully uploaded to PyPI!$(NC)"

.PHONY: release
release: quality test build-check ## Full release process
	@echo "$(GREEN)🚀 Starting release process...$(NC)"
	@echo "$(YELLOW)📋 Release checklist:$(NC)"
	@echo "  ✅ Code quality checks passed"
	@echo "  ✅ All tests passed"  
	@echo "  ✅ Package built and verified"
	@echo ""
	@echo "$(RED)⚠️ Ready to upload to PyPI? Press Ctrl+C to cancel, Enter to continue$(NC)"
	@read
	$(MAKE) upload
	@echo "$(GREEN)🎉 Release complete!$(NC)"

# ==================================================
# Development Commands  
# ==================================================

.PHONY: run-example
run-example: ## Run example analysis on a test repository
	@echo "$(GREEN)🔍 Running example analysis...$(NC)"
	py-github-analyzer https://github.com/octocat/Hello-World --format detailed --verbose
	@echo "$(GREEN)✅ Example analysis complete!$(NC)"

.PHONY: profile
profile: ## Profile the application performance
	@echo "$(GREEN)📊 Profiling application performance...$(NC)"
	$(PYTHON) -m cProfile -o profile.stats -m $(PACKAGE_NAME).cli --help
	$(PYTHON) -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
	@echo "$(GREEN)✅ Profiling complete! Check profile.stats$(NC)"

.PHONY: docs
docs: ## Generate and serve documentation (placeholder)
	@echo "$(YELLOW)📚 Documentation generation not implemented yet$(NC)"
	@echo "$(YELLOW)💡 Consider adding: sphinx, mkdocs, or similar$(NC)"

.PHONY: update-deps
update-deps: ## Update all dependencies
	@echo "$(GREEN)⬆️ Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e .[dev]
	@echo "$(GREEN)✅ Dependencies updated!$(NC)"

.PHONY: freeze-deps
freeze-deps: ## Freeze current dependencies to requirements files
	@echo "$(GREEN)❄️ Freezing dependencies...$(NC)"
	$(PIP) freeze > requirements-freeze.txt
	$(PIP) list --format=freeze > requirements-full.txt
	@echo "$(GREEN)✅ Dependencies frozen to requirements-*.txt$(NC)"

# ==================================================
# CI/CD Commands
# ==================================================

.PHONY: ci
ci: quality test security-check build-check ## Run complete CI pipeline locally
	@echo "$(GREEN)🔄 Running complete CI pipeline...$(NC)"
	@echo "$(GREEN)✅ CI pipeline completed successfully!$(NC)"
	@echo "$(YELLOW)📋 Summary:$(NC)"
	@echo "  ✅ Code formatting and linting"
	@echo "  ✅ Type checking" 
	@echo "  ✅ All tests passed"
	@echo "  ✅ Security checks completed"
	@echo "  ✅ Package build verified"

.PHONY: pre-commit
pre-commit: ## Install pre-commit hooks
	@echo "$(GREEN)🪝 Installing pre-commit hooks...$(NC)"
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✅ Pre-commit hooks installed!$(NC)"

.PHONY: validate
validate: ## Validate package configuration and dependencies
	@echo "$(GREEN)✔️ Validating package configuration...$(NC)"
	$(PYTHON) -m py_github_analyzer.cli --version
	$(PIP) check
	@echo "$(GREEN)✅ Package validation complete!$(NC)"

# ==================================================
# Quick Development Shortcuts
# ==================================================

.PHONY: dev
dev: quality-fix test ## Quick development cycle: fix code + run tests
	@echo "$(GREEN)⚡ Quick development cycle complete!$(NC)"

.PHONY: check
check: quality test ## Quick check: run quality checks + tests  
	@echo "$(GREEN)✅ Quick check complete!$(NC)"

.PHONY: fix
fix: format lint ## Quick fix: format code + basic linting
	@echo "$(GREEN)🛠️ Code fixes applied!$(NC)"

# ==================================================
# Platform-specific helpers
# ==================================================

.PHONY: install-windows
install-windows: ## Windows-specific development setup
	@echo "$(GREEN)🪟 Setting up for Windows development...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(MAKE) install-dev
	@echo "$(GREEN)✅ Windows development setup complete!$(NC)"

.PHONY: install-mac
install-mac: ## macOS-specific development setup  
	@echo "$(GREEN)🍎 Setting up for macOS development...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(MAKE) install-dev
	@echo "$(GREEN)✅ macOS development setup complete!$(NC)"

.PHONY: install-linux
install-linux: ## Linux-specific development setup
	@echo "$(GREEN)🐧 Setting up for Linux development...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(MAKE) install-dev
	@echo "$(GREEN)✅ Linux development setup complete!$(NC)"

# ==================================================
# Troubleshooting
# ==================================================

.PHONY: doctor
doctor: ## Diagnose common development environment issues
	@echo "$(GREEN)👩‍⚕️ Running environment diagnostics...$(NC)"
	@echo ""
	@echo "$(BOLD)Python Environment:$(NC)"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Python location: $$(which $(PYTHON))"
	@echo "Pip version: $$($(PIP) --version)"
	@echo ""
	@echo "$(BOLD)Package Information:$(NC)"
	@$(PIP) show $(PACKAGE_NAME) 2>/dev/null || echo "Package not installed"
	@echo ""
	@echo "$(BOLD)Development Dependencies:$(NC)"
	@$(PIP) check 2>/dev/null && echo "✅ All dependencies satisfied" || echo "❌ Dependency conflicts detected"
	@echo ""
	@echo "$(BOLD)Directory Structure:$(NC)"
	@echo "Package directory: $$(ls -la $(PACKAGE_NAME)/ 2>/dev/null | wc -l) files" 
	@echo "Test directory: $$(ls -la $(TEST_DIR)/ 2>/dev/null | wc -l) files"
	@echo ""
	@echo "$(GREEN)🏥 Diagnostic complete!$(NC)"

# ==================================================
# Advanced Development
# ==================================================

.PHONY: benchmark
benchmark: ## Run performance benchmarks
	@echo "$(GREEN)⏱️ Running performance benchmarks...$(NC)"
	@echo "$(YELLOW)💡 Benchmark suite not implemented yet$(NC)"
	@echo "$(YELLOW)Consider adding: pytest-benchmark or custom timing tests$(NC)"

.PHONY: memory-profile
memory-profile: ## Profile memory usage
	@echo "$(GREEN)🧠 Profiling memory usage...$(NC)"
	@echo "$(YELLOW)💡 Memory profiling not implemented yet$(NC)"
	@echo "$(YELLOW)Consider adding: memory-profiler or pympler$(NC)"

# ==================================================
# Error Handling
# ==================================================

# Ensure commands fail properly
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
