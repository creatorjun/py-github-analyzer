"""
py-github-analyzer - GitHub repository analyzer with AI-optimized code extraction

A high-performance tool for analyzing GitHub repositories and generating metadata
Enhanced with optimized access flow and comprehensive private repository support

Usage:
    import py_github_analyzer as pga
    result = pga.analyze_repository("https://github.com/user/repo")
    
    # Simple usage
    analyzer = pga.GitHubAnalyzer()
    result = analyzer.analyze_repository("repo_url")
    
    # Async analysis (recommended for better performance)
    result = await pga.analyze_repository_async("https://github.com/user/repo")
    
    # Private repository access
    result = pga.analyze_repository("https://github.com/user/private-repo", github_token="YOUR_TOKEN")

Version: 1.0.0 - Official Release
"""

__version__ = "1.0.0"
__author__ = "Han Jun-hee"
__email__ = "createbrain2heart@gmail.com"

# Import existing classes (already implemented)
try:
    from .core import GitHubRepositoryAnalyzer as CoreAnalyzer
    from .async_github_client import AsyncGitHubClient as AsyncClient
    
    # Clean and consistent main interfaces
    GitHubAnalyzer = CoreAnalyzer  # Main analyzer class
    AsyncGitHubAnalyzer = AsyncClient  # Async analyzer class
    
    # Backward compatibility aliases for existing code
    Analyzer = GitHubAnalyzer
    AsyncAnalyzer = AsyncGitHubAnalyzer
    GitHubRepositoryAnalyzer = GitHubAnalyzer  # Support original long name


    def analyze_repository(repo_url, output_dir="./results", output_format="bin", **kwargs):
        """
        Analyze GitHub repository - convenience function with enhanced private repo support
        
        Args:
            repo_url (str): GitHub repository URL
            output_dir (str): Output directory for results
            output_format (str): Output format ('json', 'bin', 'both')
            **kwargs: Additional options (github_token, method, verbose, etc.)
        
        Returns:
            dict: Analysis results containing metadata, files, and processing info
            
        Examples:
            # Public repository
            result = analyze_repository("https://github.com/user/repo")
            
            # Private repository
            result = analyze_repository(
                "https://github.com/user/private-repo",
                github_token="your_github_token"
            )
            
            # Custom output
            result = analyze_repository(
                "https://github.com/user/repo",
                output_dir="./my-results",
                output_format="both",
                method="zip"
            )
            
            print(f"Languages: {result['metadata']['lang']}")
            print(f"Files: {result['metadata']['files']}")
        """
        analyzer = GitHubAnalyzer()
        return analyzer.analyze_repository(repo_url, output_dir, output_format, **kwargs)


    async def analyze_repository_async(repo_url, output_dir="./results", output_format="bin", **kwargs):
        """
        Analyze GitHub repository asynchronously - high-performance convenience function
        
        Args:
            repo_url (str): GitHub repository URL
            output_dir (str): Output directory for results
            output_format (str): Output format ('json', 'bin', 'both')
            **kwargs: Additional options (github_token, method, verbose, etc.)
        
        Returns:
            dict: Analysis results containing metadata, files, and processing info
            
        Examples:
            # Async analysis (recommended)
            result = await analyze_repository_async("https://github.com/user/repo")
            
            # Multiple repositories concurrently
            import asyncio
            
            repos = [
                "https://github.com/user/repo1",
                "https://github.com/user/repo2",
                "https://github.com/user/repo3"
            ]
            
            async def analyze_multiple():
                tasks = [analyze_repository_async(repo) for repo in repos]
                results = await asyncio.gather(*tasks)
                return results
            
            results = asyncio.run(analyze_multiple())
            
            # Private repository with token
            result = await analyze_repository_async(
                "https://github.com/user/private-repo",
                github_token="your_token"
            )
            
            print(f"Languages: {result['metadata']['lang']}")
        """
        # Import here to avoid circular import
        from .async_github_client import analyze_repository_async as async_func
        return await async_func(repo_url, output_dir, output_format, **kwargs)


    # Enhanced async availability check function
    def is_async_available():
        """
        Check if async functionality is available with detailed information
        
        Returns:
            bool: True if async dependencies are installed, False otherwise
            
        Examples:
            if is_async_available():
                print("✅ Async support available - use analyze_repository_async() for better performance")
                result = await analyze_repository_async(repo_url)
            else:
                print("⚠️  Async support limited - install 'httpx aiofiles' for full async support")
                result = analyze_repository(repo_url)
        """
        try:
            import httpx
            import aiofiles
            # Test basic functionality
            httpx.AsyncClient()
            return True
        except ImportError:
            return False
        except Exception:
            # Dependencies exist but might have issues
            return False


    # Convenience functions for quick usage
    __all__ = [
        # Main classes
        'GitHubAnalyzer', 'AsyncGitHubAnalyzer',
        # Convenience functions  
        'analyze_repository', 'analyze_repository_async',
        # Backward compatibility aliases
        'Analyzer', 'AsyncAnalyzer', 'GitHubRepositoryAnalyzer',
        # Utility functions
        'get_version', 'get_package_info', 'is_async_available',
        # Helper functions
        'show_usage_examples', 'get_supported_formats', 'get_supported_methods'
    ]

except ImportError as e:
    print(f"Warning: Failed to import some modules: {e}")
    
    # Fallback for is_async_available when imports fail
    def is_async_available():
        """Check if async functionality is available (fallback)"""
        try:
            import httpx
            import aiofiles
            return True
        except ImportError:
            return False
    
    __all__ = ['is_async_available']  # Minimal fallback export list

# Utility functions
def get_version():
    """Return package version"""
    return __version__

def get_package_info():
    """
    Return comprehensive package information dictionary
    
    Returns:
        dict: Package metadata including name, version, author, features, etc.
    """
    return {
        "name": "py-github-analyzer",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": "GitHub repository analyzer with AI-optimized code extraction and enhanced private repository support",
        "main_classes": ["GitHubAnalyzer", "AsyncGitHubAnalyzer"],
        "convenience_functions": ["analyze_repository", "analyze_repository_async"],
        "package_url": "https://github.com/creatorjun/py-github-analyzer",
        "pypi_url": "https://pypi.org/project/py-github-analyzer/",
        "documentation_url": "https://github.com/creatorjun/py-github-analyzer/blob/main/README.md",
        "features": [
            "🎯 Optimized ZIP-first access strategy",
            "🔒 Enhanced private repository support with smart detection",
            "⚡ Native async/await support with high-performance parallel processing", 
            "🎯 AI-optimized output format for machine learning applications",
            "📊 Smart language detection and file prioritization",
            "🛡️ Comprehensive error handling with user-friendly guidance",
            "🔧 Multiple download methods (ZIP, API, auto-selection)",
            "📈 Advanced rate limit management and token optimization",
            "🔍 Intelligent branch detection and fallback mechanisms",
            "💾 Multiple output formats (JSON, compressed binary)"
        ],
        "supported_formats": ["json", "bin", "both"],
        "supported_methods": ["auto", "zip", "api"],
        "async_available": is_async_available(),
        "version_info": {
            "major": 1,
            "minor": 0,
            "patch": 0,
            "release_type": "stable"
        }
    }

def get_supported_formats():
    """Get list of supported output formats"""
    return ["json", "bin", "both"]

def get_supported_methods():
    """Get list of supported download methods"""
    return ["auto", "zip", "api"]

def show_usage_examples():
    """Print comprehensive usage examples to console"""
    examples = f"""
py-github-analyzer v{__version__} Usage Examples:

🚀 QUICK START
==============

1. Basic Analysis (Recommended)
   import py_github_analyzer as pga
   result = pga.analyze_repository("https://github.com/user/repo")
   print(f"Languages: {{result['metadata']['lang']}}")

2. High-Performance Async Analysis  
   import asyncio
   import py_github_analyzer as pga
   
   async def analyze():
       result = await pga.analyze_repository_async("https://github.com/user/repo")
       return result
   
   result = asyncio.run(analyze())
   print(f"Files analyzed: {{result['metadata']['files']}}")

🔒 PRIVATE REPOSITORY ACCESS
============================

3. Private Repository with Token
   import py_github_analyzer as pga
   
   result = pga.analyze_repository(
       "https://github.com/user/private-repo",
       github_token="ghp_your_token_here"
   )

4. Error Handling for Private Repos
   import py_github_analyzer as pga
   from py_github_analyzer.exceptions import PrivateRepositoryError
   
   try:
       result = pga.analyze_repository("https://github.com/user/private-repo")
   except PrivateRepositoryError as e:
       print("🔒 Private repository detected!")
       print("Get a token at: https://github.com/settings/tokens")
       print("Then use: pga.analyze_repository(url, github_token='YOUR_TOKEN')")

⚡ HIGH-PERFORMANCE FEATURES
============================

5. Concurrent Multiple Repository Analysis
   import asyncio
   import py_github_analyzer as pga
   
   async def analyze_multiple_repos():
       repos = [
           "https://github.com/user/repo1",
           "https://github.com/user/repo2", 
           "https://github.com/user/repo3"
       ]
       
       tasks = [pga.analyze_repository_async(repo) for repo in repos]
       results = await asyncio.gather(*tasks)
       
       for i, result in enumerate(results):
           print(f"Repo {{i+1}}: {{result['metadata']['files']}} files")
       
       return results
   
   results = asyncio.run(analyze_multiple_repos())

6. Object-Oriented Approach with Custom Settings
   import py_github_analyzer as pga
   
   analyzer = pga.GitHubAnalyzer()
   result = analyzer.analyze_repository(
       "https://github.com/user/repo",
       output_dir="./custom-results",
       output_format="both",  # JSON + Binary
       method="zip",         # Force ZIP method
       github_token="your_token"
   )

🔧 ADVANCED CONFIGURATION
=========================

7. Method Selection and Output Control
   import py_github_analyzer as pga
   
   # Force specific download method
   result = pga.analyze_repository(
       "https://github.com/user/large-repo",
       method="zip"  # or "api", "auto"
   )
   
   # Custom output formats
   result = pga.analyze_repository(
       "https://github.com/user/repo",
       output_format="json",    # Human-readable
       output_dir="./results"
   )

8. Feature Detection and Compatibility
   import py_github_analyzer as pga
   
   print(f"Version: {{pga.get_version()}}")
   
   # Check async availability
   if pga.is_async_available():
       print("✅ High-performance async mode available")
       result = await pga.analyze_repository_async(url)
   else:
       print("⚠️  Install 'httpx aiofiles' for async support")
       result = pga.analyze_repository(url)
   
   # Get comprehensive package info
   info = pga.get_package_info()
   print(f"Features: {{len(info['features'])}} available")
   for feature in info['features']:
       print(f"   {feature}")

🔑 GITHUB TOKEN SETUP GUIDE
============================

9. Token Creation and Management
   # 1. Visit: https://github.com/settings/tokens
   # 2. Click 'Generate new token (classic)'
   # 3. Select scopes:
   #    • 'repo' - for private repositories (recommended)
   #    • 'public_repo' - for public repositories only
   # 4. Copy the generated token (starts with 'ghp_' or 'github_pat_')
   
   # Usage in code:
   token = "ghp_xxxxxxxxxxxxxxxxxxxx"  # Your actual token
   result = pga.analyze_repository(repo_url, github_token=token)

📊 WORKING WITH RESULTS
=======================

10. Extracting Useful Information
    import py_github_analyzer as pga
    
    result = pga.analyze_repository("https://github.com/user/repo")
    
    # Repository metadata
    metadata = result['metadata']
    print(f"Repository: {{metadata['repo']}}")
    print(f"Languages: {{metadata['lang']}}")
    print(f"File count: {{metadata['files']}}")
    print(f"Total size: {{metadata['size'] / 1024:.2f}} KB")
    
    # File information
    files = result['files']
    for file_info in files[:5]:  # Show first 5 files
        print(f"{{file_info['path']}}: {{len(file_info['content'])}} chars")
    
    # Output paths
    paths = result['output_paths']
    print(f"Results saved to: {{paths}}")

🆘 TROUBLESHOOTING
==================

Common Issues and Solutions:

• Private Repository Access:
  Solution: Get a token at https://github.com/settings/tokens
  Usage: pga.analyze_repository(url, github_token='YOUR_TOKEN')

• Rate Limit Exceeded:
  Solution: Use a GitHub token for higher limits (5000 vs 60 per hour)

• Large Repository Timeout:
  Solution: Use method="zip" for faster bulk download

• Async Import Errors:
  Solution: pip install httpx aiofiles

📞 SUPPORT & INFORMATION
========================

• GitHub: https://github.com/creatorjun/py-github-analyzer
• PyPI: https://pypi.org/project/py-github-analyzer/
• Email: {__email__}
• Version: {__version__} - Official Release with Enhanced Private Repository Support

🏆 KEY IMPROVEMENTS IN v{__version__}
=====================================

✅ ZIP-first access strategy for optimal performance
✅ Enhanced private repository detection and user guidance
✅ Advanced async support with parallel processing
✅ Comprehensive error handling and recovery mechanisms
✅ Smart rate limit management and token optimization
✅ Intelligent branch detection with fallback support
✅ Multiple output formats optimized for AI applications
"""
    print(examples)

# Package-level constants for v1.0.0
DEFAULT_OUTPUT_DIR = "./results"
DEFAULT_OUTPUT_FORMAT = "bin"
SUPPORTED_FORMATS = ["json", "bin", "both"]
SUPPORTED_METHODS = ["auto", "zip", "api"]

# Feature flags for v1.0.0
PRIVATE_REPO_SUPPORT = True
ASYNC_SUPPORT = is_async_available()
CLI_SUPPORT = True
ZIP_FIRST_STRATEGY = True
ENHANCED_ERROR_HANDLING = True
PARALLEL_PROCESSING = True

# Version info
VERSION_INFO = {
    "major": 1,
    "minor": 0, 
    "patch": 0,
    "release_type": "stable",
    "release_date": "2025-10-04",
    "key_features": [
        "ZIP-first access optimization",
        "Enhanced private repository support", 
        "Advanced async parallel processing",
        "Comprehensive error handling",
        "Smart token management"
    ]
}

# Compatibility information
PYTHON_REQUIRES = ">=3.7"
DEPENDENCIES_REQUIRED = ["requests", "rich"]
DEPENDENCIES_OPTIONAL = ["httpx", "aiofiles"]  # For async support

def get_system_info():
    """Get system and dependency information"""
    import sys
    
    info = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "package_version": __version__,
        "async_available": is_async_available(),
        "dependencies": {
            "required": DEPENDENCIES_REQUIRED,
            "optional": DEPENDENCIES_OPTIONAL,
            "installed": []
        }
    }
    
    # Check which dependencies are installed
    for dep in DEPENDENCIES_REQUIRED + DEPENDENCIES_OPTIONAL:
        try:
            __import__(dep)
            info["dependencies"]["installed"].append(dep)
        except ImportError:
            pass
    
    return info
