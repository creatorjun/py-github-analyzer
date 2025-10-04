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

# Core imports - ASYNC ONLY
from .core import (
    GitHubRepositoryAnalyzer,
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

def get_version():
    """Get package version"""
    return __version__

def check_env_file():
    """Check .env file status and token availability"""
    if not TOKEN_UTILS_AVAILABLE:
        return {
            'env_support': False,
            'error': 'TokenUtils not available'
        }
    
    try:
        env_files = TokenUtils._find_env_files()
        env_vars = TokenUtils._load_env_variables()
        
        return {
            'env_files_found': len(env_files),
            'env_file_paths': env_files,
            'github_token_in_env': bool(env_vars.get('GITHUB_TOKEN')),
            'gh_token_in_env': bool(env_vars.get('GH_TOKEN'))
        }
    except Exception as e:
        return {
            'env_support': True,
            'error': str(e),
            'env_files_found': 0
        }

def get_token_sources():
    """Get available token sources"""
    if not TOKEN_UTILS_AVAILABLE:
        return {'error': 'TokenUtils not available'}
    
    try:
        import os
        sources = {}
        
        # System environment
        if os.environ.get('GITHUB_TOKEN'):
            sources['GITHUB_TOKEN_system'] = 'system environment'
        if os.environ.get('GH_TOKEN'):
            sources['GH_TOKEN_system'] = 'system environment'
        
        # .env files
        env_vars = TokenUtils._load_env_variables()
        if env_vars.get('GITHUB_TOKEN'):
            sources['GITHUB_TOKEN_env'] = '.env file'
        if env_vars.get('GH_TOKEN'):
            sources['GH_TOKEN_env'] = '.env file'
            
        return sources
    except Exception as e:
        return {'error': str(e)}

# Export main components
__all__ = [
    # Main classes and functions - ASYNC ONLY
    'GitHubRepositoryAnalyzer',
    'analyze_repository_async',
    'AsyncGitHubClient',
    
    # Aliases
    'Analyzer', 
    'GitHubAnalyzer',
    
    # Utility functions
    'get_version',
    'check_env_file',
    'get_token_sources',
    
    # Version info
    '__version__'
]

# Print initialization info
def _print_init_info():
    """Print package initialization information"""
    try:
        token_status = "✅ Available" if TOKEN_UTILS_AVAILABLE else "❌ Not available"
        print(f"py-github-analyzer v{__version__}")
        print(f"  • Async support: ✅ Available")
        print(f"  • .env support: {token_status}")
    except:
        pass  # Silent init

# Only print info in development mode
import os
if os.environ.get('PY_GITHUB_ANALYZER_DEBUG'):
    _print_init_info()
