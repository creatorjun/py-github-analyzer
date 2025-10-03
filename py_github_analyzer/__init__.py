"""
py-github-analyzer - GitHub repository analyzer with AI-optimized code extraction

A high-performance tool for analyzing GitHub repositories and generating metadata
Enhanced with optimized access flow and comprehensive private repository support

Usage:
    # Simple usage
    import py_github_analyzer as pga
    result = pga.analyze_repository("https://github.com/user/repo")
    
    # Advanced usage
    analyzer = pga.GitHubAnalyzer()
    result = analyzer.analyze_repository(repo_url)
    
    # Async analysis (recommended for better performance)
    result = await pga.analyze_repository_async("https://github.com/user/repo")
    
    # Private repository access
    result = pga.analyze_repository("https://github.com/user/private-repo", github_token="YOUR_TOKEN")

Version: 1.0.0 - Official Release
"""

__version__ = "1.0.0"
__author__ = "Han Jun-hee"
__email__ = "createbrain2heart@gmail.com"

# Try to import existing classes (already implemented)
try:
    from .core import GitHubRepositoryAnalyzer as CoreAnalyzer
    from .async_github_client import AsyncGitHubClient as AsyncClient
    
    # Main analyzer class
    GitHubAnalyzer = CoreAnalyzer  # Alias for backward compatibility
    AsyncGitHubAnalyzer = AsyncClient  # Alias for async operations
    
    # Import utility functions
    from .utils import URLParser
    from .config import Config
    from .logger import AnalyzerLogger
    from .exceptions import GitHubAnalyzerError
    
    ASYNC_AVAILABLE = True
    
except ImportError as e:
    # Fallback imports if some modules are missing
    print(f"Warning: Some modules unavailable: {e}")
    GitHubAnalyzer = None
    AsyncGitHubAnalyzer = None
    ASYNC_AVAILABLE = False

# High-level convenience functions
def analyze_repository(
    repo_url: str,
    output_dir: str = "./results",
    output_format: str = "bin",
    github_token: str = None,
    method: str = "auto",
    verbose: bool = False,
    dry_run: bool = False,
    fallback: bool = True,
    **kwargs
):
    """
    Analyze a GitHub repository and generate optimized code extraction
    
    Args:
        repo_url (str): GitHub repository URL
        output_dir (str): Output directory for results (default: "./results")
        output_format (str): Output format - 'json', 'bin', or 'both' (default: "bin")
        github_token (str): GitHub personal access token for private repositories
        method (str): Analysis method - 'auto', 'zip', or 'api' (default: "auto")
        verbose (bool): Enable verbose logging (default: False)
        dry_run (bool): Perform dry run without saving files (default: False)
        fallback (bool): Enable fallback strategies on failure (default: True)
        **kwargs: Additional options
        
    Returns:
        dict: Analysis results with metadata, files, and output paths
        
    Example:
        # Basic usage
        result = analyze_repository("https://github.com/user/repo")
        
        # With private repository
        result = analyze_repository(
            "https://github.com/user/private-repo",
            github_token="ghp_xxxxxxxxxxxx"
        )
        
        # Advanced options
        result = analyze_repository(
            "https://github.com/user/repo",
            output_dir="./my_results",
            output_format="both",
            verbose=True
        )
    """
    if not GitHubAnalyzer:
        raise ImportError("GitHubAnalyzer not available. Please check your installation.")
    
    try:
        analyzer = GitHubAnalyzer(
            token=github_token,
            logger=AnalyzerLogger(verbose=verbose)
        )
        
        return analyzer.analyze_repository(
            repo_url=repo_url,
            output_dir=output_dir,
            output_format=output_format,
            method=method,
            dry_run=dry_run,
            fallback=fallback,
            **kwargs
        )
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'metadata': {},
            'files': [],
            'output_paths': {}
        }

async def analyze_repository_async(
    repo_url: str,
    output_dir: str = "./results",
    output_format: str = "bin",
    github_token: str = None,
    method: str = "auto",
    verbose: bool = False,
    dry_run: bool = False,
    fallback: bool = True,
    **kwargs
):
    """
    Asynchronously analyze a GitHub repository with enhanced performance
    
    Args:
        repo_url (str): GitHub repository URL
        output_dir (str): Output directory for results (default: "./results")
        output_format (str): Output format - 'json', 'bin', or 'both' (default: "bin")
        github_token (str): GitHub personal access token for private repositories
        method (str): Analysis method - 'auto', 'zip', or 'api' (default: "auto")
        verbose (bool): Enable verbose logging (default: False)
        dry_run (bool): Perform dry run without saving files (default: False)
        fallback (bool): Enable fallback strategies on failure (default: True)
        **kwargs: Additional options
        
    Returns:
        dict: Analysis results with metadata, files, and output paths
        
    Example:
        # Basic async usage
        result = await analyze_repository_async("https://github.com/user/repo")
        
        # With private repository
        result = await analyze_repository_async(
            "https://github.com/user/private-repo",
            github_token="ghp_xxxxxxxxxxxx"
        )
        
        # Advanced async options
        result = await analyze_repository_async(
            "https://github.com/user/repo",
            output_dir="./my_results",
            output_format="both",
            verbose=True
        )
    """
    if not ASYNC_AVAILABLE:
        raise ImportError("Async functionality not available. Please install httpx: pip install httpx")
    
    # Import the actual async function
    from .async_github_client import analyze_repository_async as async_func
    
    return await async_func(
        repo_url=repo_url,
        output_dir=output_dir,
        output_format=output_format,
        github_token=github_token,
        method=method,
        verbose=verbose,
        dry_run=dry_run,
        fallback=fallback,
        **kwargs
    )

def get_version():
    """Get current version of py-github-analyzer"""
    return __version__

def check_requirements():
    """
    Check if all required dependencies are available
    
    Returns:
        dict: Status of dependencies
    """
    dependencies = {
        'core': False,
        'async': False,
        'requests': False,
        'httpx': False,
        'rich': False
    }
    
    # Check core functionality
    try:
        from .core import GitHubRepositoryAnalyzer
        dependencies['core'] = True
    except ImportError:
        pass
    
    # Check async functionality
    try:
        from .async_github_client import AsyncGitHubClient
        dependencies['async'] = True
    except ImportError:
        pass
    
    # Check requests
    try:
        import requests
        dependencies['requests'] = True
    except ImportError:
        pass
    
    # Check httpx for async
    try:
        import httpx
        dependencies['httpx'] = True
    except ImportError:
        pass
    
    # Check rich for logging
    try:
        from rich.console import Console
        dependencies['rich'] = True
    except ImportError:
        pass
    
    return dependencies

def create_analyzer(token: str = None, verbose: bool = False):
    """
    Create a GitHubAnalyzer instance with optional configuration
    
    Args:
        token (str): GitHub personal access token
        verbose (bool): Enable verbose logging
        
    Returns:
        GitHubAnalyzer: Configured analyzer instance
        
    Example:
        analyzer = create_analyzer(token="ghp_xxxxxxxxxxxx", verbose=True)
        result = analyzer.analyze_repository("https://github.com/user/repo")
    """
    if not GitHubAnalyzer:
        raise ImportError("GitHubAnalyzer not available. Please check your installation.")
    
    return GitHubAnalyzer(
        token=token,
        logger=AnalyzerLogger(verbose=verbose)
    )

async def create_async_analyzer(token: str = None, verbose: bool = False):
    """
    Create an AsyncGitHubClient instance with optional configuration
    
    Args:
        token (str): GitHub personal access token
        verbose (bool): Enable verbose logging
        
    Returns:
        AsyncGitHubClient: Configured async analyzer instance
        
    Example:
        async with create_async_analyzer(token="ghp_xxxxxxxxxxxx", verbose=True) as analyzer:
            result = await analyzer.analyze_repository("owner", "repo")
    """
    if not ASYNC_AVAILABLE:
        raise ImportError("Async functionality not available. Please install httpx: pip install httpx")
    
    return AsyncClient(
        token=token,
        logger=AnalyzerLogger(verbose=verbose)
    )

# Utility functions for common operations
def parse_github_url(url: str):
    """
    Parse GitHub URL and extract owner/repo information
    
    Args:
        url (str): GitHub repository URL
        
    Returns:
        dict: Parsed URL components
        
    Example:
        info = parse_github_url("https://github.com/user/repo")
        print(info['owner'], info['repo'])  # "user", "repo"
    """
    return URLParser.parse_github_url(url)

def validate_github_url(url: str) -> bool:
    """
    Validate if URL is a proper GitHub repository URL
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid GitHub URL
        
    Example:
        is_valid = validate_github_url("https://github.com/user/repo")
    """
    try:
        URLParser.parse_github_url(url)
        return True
    except:
        return False

def get_supported_formats():
    """Get list of supported output formats"""
    return ['json', 'bin', 'both']

def get_supported_methods():
    """Get list of supported analysis methods"""
    return ['auto', 'zip', 'api']

# Configuration helpers
def get_default_config():
    """Get default configuration settings"""
    return {
        'output_dir': './results',
        'output_format': 'bin',
        'method': 'auto',
        'verbose': False,
        'dry_run': False,
        'fallback': True,
        'max_file_size_mb': Config.MAX_FILE_SIZE_BYTES // (1024 * 1024),
        'max_total_size_mb': Config.MAX_TOTAL_SIZE_MB,
        'timeout_seconds': Config.TIMEOUT_CONFIG['http_timeout']
    }

def create_custom_config(**kwargs):
    """
    Create custom configuration with validation
    
    Args:
        **kwargs: Configuration parameters
        
    Returns:
        dict: Validated configuration
        
    Example:
        config = create_custom_config(
            output_dir="./custom_results",
            verbose=True,
            output_format="both"
        )
    """
    default_config = get_default_config()
    
    # Validate output format
    if 'output_format' in kwargs:
        if kwargs['output_format'] not in get_supported_formats():
            raise ValueError(f"Invalid output_format: {kwargs['output_format']}")
    
    # Validate method
    if 'method' in kwargs:
        if kwargs['method'] not in get_supported_methods():
            raise ValueError(f"Invalid method: {kwargs['method']}")
    
    # Update with provided values
    default_config.update(kwargs)
    return default_config

# Export main classes and functions
__all__ = [
    # Main classes
    'GitHubAnalyzer',
    'AsyncGitHubAnalyzer',
    
    # Main functions
    'analyze_repository',
    'analyze_repository_async',
    
    # Factory functions
    'create_analyzer',
    'create_async_analyzer',
    
    # Utility functions
    'parse_github_url',
    'validate_github_url',
    'get_version',
    'check_requirements',
    'get_supported_formats',
    'get_supported_methods',
    'get_default_config',
    'create_custom_config',
    
    # Core classes (for advanced usage)
    'URLParser',
    'Config',
    'AnalyzerLogger',
    'GitHubAnalyzerError',
    
    # Version info
    '__version__',
    '__author__',
    '__email__'
]

# Backward compatibility aliases
analyze_repo = analyze_repository  # Short alias
analyze_repo_async = analyze_repository_async  # Short async alias

# Module initialization message (only shown in verbose mode)
def _init_message():
    """Show initialization message if verbose logging is enabled"""
    import os
    if os.environ.get('PY_GITHUB_ANALYZER_VERBOSE'):
        print(f"py-github-analyzer v{__version__} initialized")
        deps = check_requirements()
        missing = [k for k, v in deps.items() if not v]
        if missing:
            print(f"Note: Optional dependencies missing: {', '.join(missing)}")

# Call initialization
_init_message()
