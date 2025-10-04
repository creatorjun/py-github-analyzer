"""
py-github-analyzer v1.0.0 - Async GitHub Repository Analyzer
High-performance GitHub repository analyzer with AI-optimized code extraction and .env support
"""

__version__ = "1.0.0"
__author__ = "Han Jun-hee" 
__email__ = "createbrain2heart@gmail.com"

# Check required dependencies
try:
    import httpx
    import asyncio
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    httpx = None

if not ASYNC_AVAILABLE:
    raise ImportError(
        "py-github-analyzer requires async dependencies.\n"
        "Install with: pip install httpx aiofiles"
    )

# Core imports
from .core import (
    GitHubRepositoryAnalyzer,
    analyze_repository,
    analyze_repository_async,
)

from .async_github_client import AsyncGitHubClient

# Import TokenUtils for .env support
try:
    from .utils import TokenUtils
    TOKEN_UTILS_AVAILABLE = True
except ImportError:
    TOKEN_UTILS_AVAILABLE = False
    TokenUtils = None

# Convenience aliases
Analyzer = GitHubRepositoryAnalyzer
GitHubAnalyzer = GitHubRepositoryAnalyzer

# Main exports
__all__ = [
    'GitHubRepositoryAnalyzer',
    'AsyncGitHubClient', 
    'analyze_repository',
    'analyze_repository_async',
    'Analyzer',
    'GitHubAnalyzer',
    'get_version',
    'TokenUtils'
]

def get_version() -> str:
    """Return package version"""
    return __version__

def get_usage_examples():
    """Return common usage examples"""
    return {
        'basic_sync': "import py_github_analyzer as pga; result = pga.analyze_repository('https://github.com/user/repo')",
        'basic_async': "result = await pga.analyze_repository_async('https://github.com/user/repo')",
        'with_token': "result = pga.analyze_repository('https://github.com/user/repo', github_token='your_token')",
        'with_env_file': "# Create .env file with GITHUB_TOKEN=your_token\nresult = pga.analyze_repository('https://github.com/user/repo')",
        'class_usage': "analyzer = pga.GitHubRepositoryAnalyzer(); result = await analyzer.analyze_repository('repo_url')"
    }

def get_token_sources():
    """Return information about token sources"""
    return {
        'priority_order': [
            '1. Function parameter (github_token=...)',
            '2. GITHUB_TOKEN environment variable',
            '3. GH_TOKEN environment variable',
            '4. .env file GITHUB_TOKEN',
            '5. .env file GH_TOKEN'
        ],
        'env_file_locations': [
            'Current working directory (.env)',
            'Parent directories (up to 3 levels)'
        ],
        'env_file_format': 'GITHUB_TOKEN=your_token_here'
    }

def check_env_file():
    """Check for .env file and return status"""
    if TOKEN_UTILS_AVAILABLE and TokenUtils:
        env_files = TokenUtils._find_env_files()
        env_vars = TokenUtils._load_env_variables()
        
        return {
            'env_files_found': len(env_files),
            'env_file_paths': env_files,
            'github_token_in_env': 'GITHUB_TOKEN' in env_vars,
            'gh_token_in_env': 'GH_TOKEN' in env_vars
        }
    
    return {
        'error': 'TokenUtils not available',
        'env_files_found': 0
    }
