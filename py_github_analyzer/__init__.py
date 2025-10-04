"""
py-github-analyzer v1.0.0 - Async GitHub Repository Analyzer
High-performance GitHub repository analyzer with AI-optimized code extraction
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
]

def get_version() -> str:
    """Return package version"""
    return __version__

# Simple usage examples for documentation
def get_usage_examples():
    """Return common usage examples"""
    return {
        'basic_sync': "import py_github_analyzer as pga; result = pga.analyze_repository('https://github.com/user/repo')",
        'basic_async': "result = await pga.analyze_repository_async('https://github.com/user/repo')",
        'with_token': "result = pga.analyze_repository('https://github.com/user/repo', github_token='your_token')",
        'class_usage': "analyzer = pga.GitHubRepositoryAnalyzer(token='your_token'); result = await analyzer.analyze_repository('repo_url')"
    }
