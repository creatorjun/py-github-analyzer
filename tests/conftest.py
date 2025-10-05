"""
Pytest configuration and shared fixtures for py-github-analyzer tests
Provides common test fixtures and utilities for all test modules
"""

import pytest
import tempfile
import shutil
import zipfile
import io
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, List, Any

from py_github_analyzer.logger import get_logger
from py_github_analyzer.exceptions import GitHubAnalyzerError

# ==================================================
# Test Configuration
# ==================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower)")
    config.addinivalue_line("markers", "async_test: Tests that use async/await")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")

# ==================================================
# Directory and File Fixtures
# ==================================================

@pytest.fixture
def temp_directory():
    """Create and cleanup temporary directory"""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def test_token():
    """GitHub test token fixture"""
    return "ghp_1234567890abcdefghijklmnopqrstuvwxyz123456"

@pytest.fixture
def sample_zip_content():
    """Sample ZIP file content for testing"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr('test-repo-main/main.py', 'print("hello")')
        zip_file.writestr('test-repo-main/utils.py', 'def helper(): return True')
        zip_file.writestr('test-repo-main/requirements.txt', 'requests\npytest')
        zip_file.writestr('test-repo-main/README.md', '# Test Repo\nA test repository')
    
    return zip_buffer.getvalue()

@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx responses"""
    def _create_response(status_code=200, json_data=None, content=None):
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.content = content or b""
        response.text = (content or b"").decode('utf-8', errors='ignore')
        response.headers = {}
        response.raise_for_status = MagicMock()
        return response
    return _create_response

@pytest.fixture
def mock_github_api_responses():
    """Mock GitHub API responses"""
    return {
        'repository_info': {
            'name': 'test-repo',
            'full_name': 'test-owner/test-repo',
            'owner': {'login': 'test-owner'},
            'language': 'Python',
            'private': False,
            'size': 1024,
            'stargazers_count': 5,
            'forks_count': 2,
            'default_branch': 'main'
        },
        'rate_limit_headers': {
            'x-ratelimit-remaining': '4999'
        },
        'tree_response': {
            'tree': [
                {'path': 'main.py', 'type': 'blob', 'size': 45},
                {'path': 'requirements.txt', 'type': 'blob', 'size': 20}
            ]
        }
    }

@pytest.fixture
def repository_analyzer(test_token, mock_logger):
    """Repository analyzer fixture (synchronous)"""
    from py_github_analyzer.core import GitHubRepositoryAnalyzer
    with patch('py_github_analyzer.core.TokenUtils.get_github_token', return_value=test_token):
        return GitHubRepositoryAnalyzer(token=test_token, logger=mock_logger)


@pytest.fixture
def sample_file_contents():
    """Sample file contents for testing"""
    return [
        {
            "path": "main.py",
            "content": 'print("Hello World")\n# Simple Python file',
            "size": 45,
            "language": "python",
            "lines": 2,
        },
        {
            "path": "utils.py",
            "content": "def helper_function():\n    return True",
            "size": 35,
            "language": "python",
            "lines": 2,
        },
        {
            "path": "package.json",
            "content": '{"name": "test", "version": "1.0.0"}',
            "size": 35,
            "language": "json",
            "lines": 1,
        },
        {
            "path": "README.md",
            "content": "# Test Repository\nThis is a test.",
            "size": 30,
            "language": "markdown",
            "lines": 2,
        },
    ]

@pytest.fixture
def sample_repository_info():
    """Sample repository information"""
    return {
        "name": "test-repo",
        "full_name": "owner/test-repo",
        "owner": "owner",
        "description": "A test repository for unit testing",
        "language": "Python",
        "topics": ["test", "python"],
        "default_branch": "main",
        "size": 1024,
        "stargazers_count": 5,
        "forks_count": 2,
        "watchers_count": 3,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-12-01T00:00:00Z",
        "pushed_at": "2023-12-01T00:00:00Z",
        "clone_url": "https://github.com/owner/test-repo.git",
        "ssh_url": "git@github.com:owner/test-repo.git",
        "homepage": "",
        "license": {"key": "mit", "name": "MIT License"},
        "private": False,
    }

# ==================================================
# Mock Fixtures
# ==================================================

@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    return logger

@pytest.fixture
def mock_github_client():
    """Mock GitHub client for testing"""
    client = AsyncMock()
    client.get_repository_info = AsyncMock()
    client.get_repository_files = AsyncMock()
    client.download_repository_zip = AsyncMock()
    client.get_file_content = AsyncMock()
    client.close = AsyncMock()
    return client

@pytest.fixture
def mock_file_processor():
    """Mock file processor for testing"""
    processor = MagicMock()
    processor.process_files = MagicMock()
    processor.detect_language = MagicMock(return_value="python")
    processor.extract_dependencies = MagicMock(return_value=[])
    processor.detect_frameworks = MagicMock(return_value=[])
    processor.calculate_complexity = MagicMock(return_value=1.0)
    return processor

@pytest.fixture
def mock_metadata_generator():
    """Mock metadata generator for testing"""
    generator = MagicMock()
    generator.generate_metadata = MagicMock()
    generator.generate_summary = MagicMock(return_value="Test summary")
    return generator

# ==================================================
# GitHub API Response Fixtures
# ==================================================

@pytest.fixture
def github_api_repository_response():
    """Sample GitHub API repository response"""
    return {
        "id": 123456,
        "name": "test-repo",
        "full_name": "owner/test-repo",
        "owner": {
            "login": "owner",
            "id": 789,
            "type": "User",
        },
        "private": False,
        "description": "A test repository",
        "language": "Python",
        "size": 1024,
        "stargazers_count": 5,
        "watchers_count": 3,
        "forks_count": 2,
        "default_branch": "main",
        "topics": ["test", "python"],
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-12-01T00:00:00Z",
        "pushed_at": "2023-12-01T00:00:00Z",
        "clone_url": "https://github.com/owner/test-repo.git",
        "ssh_url": "git@github.com:owner/test-repo.git",
        "homepage": None,
        "license": {
            "key": "mit",
            "name": "MIT License",
            "url": "https://api.github.com/licenses/mit",
        },
    }

@pytest.fixture
def github_api_contents_response():
    """Sample GitHub API contents response"""
    return [
        {
            "name": "main.py",
            "path": "main.py",
            "type": "file",
            "size": 45,
            "download_url": "https://raw.githubusercontent.com/owner/test-repo/main/main.py",
        },
        {
            "name": "utils.py",
            "path": "utils.py",
            "type": "file",
            "size": 35,
            "download_url": "https://raw.githubusercontent.com/owner/test-repo/main/utils.py",
        },
        {
            "name": "README.md",
            "path": "README.md",
            "type": "file",
            "size": 30,
            "download_url": "https://raw.githubusercontent.com/owner/test-repo/main/README.md",
        },
        {
            "name": "src",
            "path": "src",
            "type": "dir",
        },
    ]

@pytest.fixture
def github_rate_limit_response():
    """Sample GitHub API rate limit response"""
    return {
        "resources": {
            "core": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1640995200,
                "used": 1,
            },
            "search": {
                "limit": 30,
                "remaining": 30,
                "reset": 1640995200,
                "used": 0,
            },
        },
        "rate": {
            "limit": 5000,
            "remaining": 4999,
            "reset": 1640995200,
            "used": 1,
        },
    }

# ==================================================
# Analysis Result Fixtures  
# ==================================================

@pytest.fixture
def sample_analysis_result():
    """Sample complete analysis result"""
    return {
        "success": True,
        "repository": {
            "name": "test-repo",
            "owner": "owner",
            "description": "Test repository",
            "language": "Python",
            "size": 1024,
            "stars": 5,
            "forks": 2,
        },
        "analysis": {
            "total_files": 4,
            "total_size": 145,
            "primary_language": "Python",
            "languages": {"Python": 55.2, "JSON": 24.1, "Markdown": 20.7},
            "complexity_score": 2.5,
            "file_count_by_type": {"python": 2, "json": 1, "markdown": 1},
        },
        "files": [
            {
                "path": "main.py",
                "size": 45,
                "language": "python",
                "lines": 2,
                "complexity": 1.0,
            },
            {
                "path": "utils.py", 
                "size": 35,
                "language": "python",
                "lines": 2,
                "complexity": 1.5,
            },
        ],
        "dependencies": ["requests", "pytest"],
        "frameworks": ["pytest"],
        "metadata": {
            "analysis_time": "2023-12-01T12:00:00Z",
            "version": "1.0.0",
            "method": "api",
        },
    }

# ==================================================
# Async Test Fixtures
# ==================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# ==================================================
# HTTP Mock Fixtures
# ==================================================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for testing"""
    client = MagicMock()
    
    # Mock response object
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock()
    response.text = ""
    response.content = b""
    response.headers = {}
    response.raise_for_status = MagicMock()
    
    # Async context manager support
    async def async_enter():
        return client
    
    async def async_exit(exc_type, exc_val, exc_tb):
        pass
    
    client.__aenter__ = async_enter
    client.__aexit__ = async_exit
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    
    return client

# ==================================================
# Error Simulation Fixtures
# ==================================================

@pytest.fixture
def network_error_client():
    """Mock client that raises network errors"""
    client = AsyncMock()
    client.get_repository_info.side_effect = GitHubAnalyzerError("Network error")
    return client

@pytest.fixture
def rate_limit_error_client():
    """Mock client that raises rate limit errors"""
    from py_github_analyzer.exceptions import RateLimitExceededError
    client = AsyncMock()
    client.get_repository_info.side_effect = RateLimitExceededError(
        "Rate limit exceeded", reset_time=1640995200, remaining=0
    )
    return client

# ==================================================
# Additional fixtures for missing test dependencies
# ==================================================

@pytest.fixture
def clean_environment(monkeypatch):
    """Clean environment without GitHub tokens"""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return monkeypatch

@pytest.fixture
def mock_token_environment(monkeypatch):
    """Environment with mock GitHub token"""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_1234567890abcdefghijklmnopqrstuvwxyz123456")
    return monkeypatch
