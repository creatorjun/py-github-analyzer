@echo off
setlocal enabledelayedexpansion

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="install-dev" goto install-dev
if "%1"=="test" goto test
if "%1"=="format" goto format
if "%1"=="format-check" goto format-check
if "%1"=="lint" goto lint
if "%1"=="quality" goto quality
if "%1"=="clean" goto clean
if "%1"=="build" goto build

echo ❌ Unknown command: %1
echo Use 'make.bat help' to see available commands
exit /b 1

:help
echo py-github-analyzer Development Commands
echo =====================================
echo.
echo Setup Commands:
echo   install      Install package in production mode
echo   install-dev  Install package in development mode
echo.
echo Testing Commands:
echo   test         Run all tests
echo.
echo Code Quality Commands:
echo   format       Format code with black and isort
echo   format-check Check code formatting
echo   lint         Run flake8 linting
echo   quality      Run all quality checks
echo.
echo Build Commands:
echo   clean        Clean build artifacts
echo   build        Build package
echo.
echo Usage: make.bat ^<command^>
goto end

:install
echo 📦 Installing py-github-analyzer...
pip install .
echo ✅ Installation complete!
goto end

:install-dev
echo 🔧 Installing development environment...
pip install -e .[dev]
echo ✅ Development installation complete!
goto end

:test
echo 🧪 Running all tests...
pytest tests -v
goto end

:format
echo 🎨 Formatting code...
black py_github_analyzer tests
isort py_github_analyzer tests
echo ✅ Code formatted!
goto end

:format-check
echo 🔍 Checking code formatting...
black --check py_github_analyzer tests
isort --check-only py_github_analyzer tests
echo ✅ Code formatting is correct!
goto end

:lint
echo 🔍 Running linting checks...
flake8 py_github_analyzer tests
echo ✅ Linting passed!
goto end

:quality
call :format-check
call :lint
echo ✨ All quality checks passed!
goto end

:clean
echo 🧹 Cleaning build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.egg-info rmdir /s /q *.egg-info
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .mypy_cache rmdir /s /q .mypy_cache
if exist htmlcov rmdir /s /q htmlcov
if exist .coverage del .coverage
if exist coverage.xml del coverage.xml
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo ✅ Cleanup complete!
goto end

:build
call :clean
echo 📦 Building package...
python -m build
echo ✅ Package built successfully!
dir dist
goto end

:end