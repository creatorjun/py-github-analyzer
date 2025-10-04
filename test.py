"""
Pytest configuration and shared fixtures for py-github-analyzer tests

Production-grade test setup with comprehensive mocking and fixtures
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional
import json
import zipfile
from io import BytesIO
import httpx

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_repository_info():
    """Sample repository information for testing"""
    return {
        'name': 'test-repo',
        'full_name': 'testuser/test-repo',
        'description': 'A test repository',
        'language': 'Python',
        'size': 1024,
        'default_branch': 'main',
        'private': False,
        'archived': False,
        'disabled': False,
        'topics': ['python', 'testing'],
        'license': {'name': 'MIT'},
        'created_at': '2023-01-01T00:00:00Z',
        'updated_at': '2023-12-01T00:00:00Z',
        'clone_url': 'https://github.com/testuser/test-repo.git',
        'html_url': 'https://github.com/testuser/test-repo',
        'stargazers_count': 42,
        'forks_count': 7
    }


@pytest.fixture
def sample_files():
    """Sample file data for testing"""
    return [
        {
            'path': 'main.py',
            'size': 500,
            'content': 'def main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()',
            'priority': 1000
        },
        {
            'path': 'utils.py',
            'size': 300,
            'content': 'def helper_function():\n    return "Helper"',
            'priority': 500
        },
        {
            'path': 'README.md',
            'size': 200,
            'content': '# Test Repository\n\nThis is a test repository.',
            'priority': 400
        },
        {
            'path': 'requirements.txt',
            'size': 100,
            'content': 'requests==2.28.0\npytest==7.0.0',
            'priority': 300
        }
    ]


@pytest.fixture
def sample_zip_content(sample_files):
    """Create sample ZIP content for testing"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for file_info in sample_files:
            zip_file.writestr(f"test-repo-main/{file_info['path']}", file_info['content'])
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.fixture
def mock_httpx_response():
    """Create mock httpx response"""
    def _create_response(status_code=200, json_data=None, content=b"", headers=None):
        response = Mock(spec=httpx.Response)
        response.status_code = status_code
        response.is_success = 200 <= status_code < 300
        response.headers = headers or {}
        response.content = content
        
        if json_data:
            response.json.return_value = json_data
        else:
            response.json.side_effect = Exception("No JSON data")
        
        return response
    return _create_response


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client"""
    from py_github_analyzer.async_github_client import AsyncGitHubClient
    
    client = Mock(spec=AsyncGitHubClient)
    client.token = "test_token"
    
    # Mock async methods
    client.analyze_repository = AsyncMock()
    client.get_repository_info = AsyncMock()
    client.download_repository_zip = AsyncMock()
    client.get_repository_tree_api = AsyncMock()
    client.download_files_concurrently = AsyncMock()
    client.get_rate_limit_info = AsyncMock()
    
    # Mock context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    
    return client


@pytest.fixture
def mock_rate_limit_manager():
    """Create mock rate limit manager"""
    from py_github_analyzer.async_github_client import AsyncRateLimitManager
    
    manager = Mock(spec=AsyncRateLimitManager)
    manager.token = "test_token"
    manager.limit = 5000
    manager.remaining = 4500
    manager.reset_time = 1640995200  # Fixed timestamp
    
    # Mock async methods
    manager.check_rate_limit = AsyncMock(return_value=True)
    manager.consume_calls = AsyncMock()
    manager.update_from_headers = AsyncMock()
    manager.wait_for_rate_limit_reset = AsyncMock()
    manager.execute_api_call = AsyncMock()
    manager.track_safe_api_call = AsyncMock()
    
    return manager


@pytest.fixture
def sample_processing_metadata():
    """Sample processing metadata for testing"""
    return {
        'languages': {'Python': 75.5, 'Markdown': 24.5},
        'primary_language': 'Python',
        'frameworks': ['pytest'],
        'dependencies': ['requests', 'pytest'],
        'total_files_processed': 4,
        'total_files_original': 10,
        'total_size_processed': 1100,
        'total_size_original': 5000,
        'size_reduction_ratio': 0.78,
        'file_type_stats': {'.py': 2, '.md': 1, '.txt': 1},
        'priority_stats': {
            'very_high_1000+': 1,
            'high_800-999': 0,
            'medium_600-799': 0,
            'normal_400-599': 1,
            'low_200-399': 1,
            'very_low_0-199': 1
        },
        'entry_points': ['main.py'],
        'processing_timestamp': 1640995200
    }


@pytest.fixture
def github_token_env(monkeypatch):
    """Set GitHub token in environment for tests"""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_from_env")
    yield "test_token_from_env"


@pytest.fixture
def no_github_token_env(monkeypatch):
    """Remove GitHub token from environment for tests"""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    yield None


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )


# Skip markers for CI/CD
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers"""
    if config.getoption("--no-network"):
        skip_network = pytest.mark.skip(reason="--no-network option given")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--no-network", 
        action="store_true", 
        default=False, 
        help="Skip network-dependent tests"
    )
    parser.addoption(
        "--run-slow", 
        action="store_true", 
        default=False, 
        help="Run slow tests"
    )
