"""
Command Line Interface for py-github-analyzer v1.0.0
Enhanced with optimized access strategy and user-friendly private repository guidance
"""

import os
import sys
from pathlib import Path

# Python version compatibility with improved error handling
try:
    if sys.version_info >= (3, 8):
        from importlib import metadata
    else:
        from importlib_metadata import metadata
except ImportError:
    metadata = None  # Fallback if metadata unavailable

import argparse
import asyncio

# Windows UTF-8 environment setup
if os.name == 'nt':  # Windows
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSFSENCODING'] = '0'

# Console encoding setup
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    # reconfigure method doesn't exist in Python 3.7
    pass
except Exception:
    # Ignore other errors
    pass

# Import with better error handling
try:
    from .core import GitHubRepositoryAnalyzer, analyze_repository, analyze_repository_async
    from .logger import get_logger, set_verbose
    from . import is_async_available
    from .config import Config
    IMPORT_SUCCESS = True
except ImportError as e:
    # Fallback imports for standalone execution
    try:
        import py_github_analyzer as pga
        GitHubRepositoryAnalyzer = pga.GitHubAnalyzer
        analyze_repository = pga.analyze_repository
        analyze_repository_async = pga.analyze_repository_async
        is_async_available = pga.is_async_available
        get_logger = lambda: print  # Simple fallback
        set_verbose = lambda x: None
        Config = type('Config', (), {'VERSION': '1.0.0'})  # Fallback config
        IMPORT_SUCCESS = True
    except ImportError:
        IMPORT_SUCCESS = False


def safe_get_version():
    """Safely get package version with multiple fallback methods"""
    
    # Method 1: Try Config class
    try:
        from .config import Config
        return Config.VERSION
    except:
        pass
    
    # Method 2: Try metadata
    if metadata:
        try:
            return metadata.version("py-github-analyzer")
        except:
            pass
    
    # Method 3: Try __init__
    try:
        from . import __version__
        return __version__
    except:
        pass
    
    # Method 4: Try package import
    try:
        import py_github_analyzer
        return py_github_analyzer.get_version()
    except:
        pass
    
    # Fallback
    return "1.0.0"


def main():
    """Main CLI entry point with enhanced error handling"""
    
    if not IMPORT_SUCCESS:
        print("❌ Error: py-github-analyzer package not properly installed or imported.", file=sys.stderr)
        print("💡 Solutions:", file=sys.stderr)
        print("   • Reinstall: pip install --upgrade py-github-analyzer", file=sys.stderr)
        print("   • Check virtual environment is activated", file=sys.stderr)
        print("   • Verify package installation: pip list | grep py-github-analyzer", file=sys.stderr)
        sys.exit(2)

    # Additional encoding setup for Windows
    if os.name == 'nt':
        import locale
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            pass

    # Get version safely
    version_string = safe_get_version()

    parser = argparse.ArgumentParser(
        description=f"py-github-analyzer v{version_string} - AI-optimized GitHub repository analysis with enhanced private repository support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
🎯 OPTIMIZED ACCESS STRATEGY (v{version_string})
============================
py-github-analyzer uses an intelligent access strategy:
• 📦 ZIP download first (fast, efficient for all repositories)
• 🔄 API fallback for private repositories (when token provided)
• 🔒 Smart private repository detection with helpful guidance

🔗 USAGE EXAMPLES
=================
  py-github-analyzer https://github.com/user/repo                    # Basic analysis (ZIP-first)
  py-github-analyzer https://github.com/user/repo --sync             # Force sync mode  
  py-github-analyzer https://github.com/user/repo -t YOUR_TOKEN      # Private repo access
  py-github-analyzer https://github.com/user/repo -f json -v         # JSON output with verbose logging
  py-github-analyzer https://github.com/user/repo -m zip             # Force ZIP method
  py-github-analyzer https://github.com/user/repo --dry-run          # Test repository access

🔑 PRIVATE REPOSITORY ACCESS
=============================
For private repositories, create a GitHub personal access token:

Step 1: Create Token
  1. Visit: https://github.com/settings/tokens
  2. Click 'Generate new token (classic)'
  3. Select 'repo' scope for private repository access
  4. Copy the generated token (starts with 'ghp_' or 'github_pat_')

Step 2: Use Token
  py-github-analyzer [PRIVATE_REPO_URL] --github-token YOUR_TOKEN

⚡ PERFORMANCE MODES
====================
• Default: Async mode (faster, parallel processing)
• --sync: Synchronous mode (more compatible, slower)
• Auto-detects best method: ZIP → API fallback

📊 OUTPUT FORMATS
==================
• bin (default): Compressed binary format optimized for AI
• json: Human-readable JSON format
• both: Generate both formats

📞 SUPPORT & DOCUMENTATION
===========================
  GitHub: https://github.com/creatorjun/py-github-analyzer
  Author: Han Jun-hee (createbrain2heart@gmail.com)
  Version: {version_string} - Official Release with ZIP-First Strategy
"""
    )

    # Positional arguments
    parser.add_argument('repo_url', 
                       nargs='?',  # Optional argument
                       help='GitHub repository URL (e.g., https://github.com/user/repo)')

    # Output options
    parser.add_argument('-o', '--output-dir', 
                       default='./results', 
                       help='Output directory (default: ./results)')

    parser.add_argument('-f', '--output-format', 
                       choices=['json', 'bin', 'both'], 
                       default='bin',
                       help='Output format: json (human-readable), bin (AI-optimized), or both (default: bin)')

    # Authentication
    parser.add_argument('-t', '--github-token', 
                       help='GitHub personal access token for private repositories and higher rate limits')

    # Analysis options
    parser.add_argument('-m', '--method', 
                       choices=['auto', 'zip', 'api'], 
                       default='auto',
                       help='Download method: auto (ZIP-first with API fallback), zip (force ZIP), or api (force API) (default: auto)')

    parser.add_argument('--sync', 
                       action='store_true',
                       help='Force synchronous mode instead of async (more compatible but slower)')

    # Utility options
    parser.add_argument('-v', '--verbose', 
                       action='store_true',
                       help='Enable detailed logging output')

    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='Test repository access without downloading files (validation only)')

    parser.add_argument('--show-examples',
                       action='store_true',
                       help='Show comprehensive usage examples and exit')

    # Information commands
    parser.add_argument('--version', 
                       action='version',
                       version=f'py-github-analyzer v{version_string} - Official Release with ZIP-First Strategy',
                       help='Show version information and exit')

    parser.add_argument('--check-features', 
                       action='store_true',
                       help='Check available features and dependencies')

    args = parser.parse_args()

    # Handle information commands FIRST (before repo_url validation)
    if args.check_features:
        check_features()
        return

    if args.show_examples:
        show_comprehensive_examples()
        return
    
    # NOW validate repo_url only if needed
    if not args.repo_url:
        logger.error("Repository URL is required for analysis")
        parser.print_help()
        sys.exit(1)

    # Setup logging
    try:
        set_verbose(args.verbose)
        logger = get_logger()
    except:
        # Fallback logger if imports failed
        logger = type('Logger', (), {
            'info': lambda self, msg: print(f"INFO: {msg}"),
            'warning': lambda self, msg: print(f"WARNING: {msg}", file=sys.stderr),
            'error': lambda self, msg: print(f"ERROR: {msg}", file=sys.stderr),
            'debug': lambda self, msg: print(f"DEBUG: {msg}") if args.verbose else None,
            'success': lambda self, msg: print(f"SUCCESS: {msg}")
        })()

    # Validate repository URL
    if not args.repo_url:
        logger.error("Repository URL is required")
        parser.print_help()
        sys.exit(1)

    try:
        # Import here to catch import errors gracefully
        from .utils import URLParser
        parsed = URLParser.parse_github_url(args.repo_url)
        logger.debug(f"Parsed repository: {parsed['owner']}/{parsed['repo']}")
    except Exception as e:
        logger.error(f"Invalid repository URL: {e}")
        logger.info("")
        logger.info("📝 Valid URL formats:")
        logger.info("  • https://github.com/user/repo")
        logger.info("  • github.com/user/repo")
        logger.info("  • user/repo")
        sys.exit(1)

    # Dry run mode
    if args.dry_run:
        logger.info("🔬 Dry run mode: Testing repository access...")
        perform_dry_run(args, logger)
        return

    # Determine execution mode
    try:
        use_async = not args.sync and is_async_available()
    except:
        use_async = not args.sync  # Fallback without availability check
    
    if args.sync:
        logger.debug("🔄 Synchronous mode requested")
    elif use_async:
        logger.debug("⚡ High-performance async mode enabled")
    else:
        logger.debug("🔄 Falling back to synchronous mode (async dependencies not available)")
        logger.info("💡 Install 'httpx aiofiles' for faster async processing")

    # Show access strategy info
    if args.verbose:
        token_status = "✅ Provided" if args.github_token else "❌ Not provided"
        logger.info(f"🔑 GitHub Token: {token_status}")
        logger.info(f"📦 Access Strategy: ZIP-first → {'API fallback (with token)' if args.github_token else 'Private repo guidance (no token)'}")
        logger.info(f"🎯 Method: {args.method}")

    # Execute analysis
    try:
        if use_async:
            try:
                result = asyncio.run(run_async_analysis(args, logger))
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    logger.warning("⚠️ Already in event loop, using sync mode...")
                    result = run_sync_analysis(args, logger)
                else:
                    raise
        else:
            result = run_sync_analysis(args, logger)

        # Show results
        if result and result.get('success', False):
            display_success_summary(result, logger)
        else:
            logger.error("❌ Analysis completed but no valid results were generated")
            logger.info("💡 Try with --verbose flag for detailed error information")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Analysis interrupted by user")
        logger.info("💡 Use Ctrl+C to cancel operations")
        sys.exit(130)
    except Exception as e:
        handle_error(e, args, logger)
        sys.exit(1)


def show_version():
    """Display comprehensive version information"""
    version_string = safe_get_version()
    
    print(f"🚀 py-github-analyzer v{version_string}")
    print("📦 Official Release with ZIP-First Strategy & Enhanced Private Repository Support")
    print("")
    print("📍 Repository: https://github.com/creatorjun/py-github-analyzer")
    print("📚 PyPI: https://pypi.org/project/py-github-analyzer/")
    print("✉️  Author: Han Jun-hee (createbrain2heart@gmail.com)")
    print("")
    
    print("🎯 Key Features:")
    features = [
        "🎯 Optimized ZIP-first access strategy",
        "🔒 Enhanced private repository support with smart detection",
        "⚡ Native async/await support with high-performance parallel processing", 
        "🎯 AI-optimized output format for machine learning applications",
        "📊 Smart language detection and file prioritization"
    ]
    for i, feature in enumerate(features, 1):
        print(f"   {i}. {feature}")
    print("")
    
    print("🔧 System Information:")
    print(f"   Python: {sys.version.split()[0]}")
    
    try:
        async_status = "✅ Available" if is_async_available() else "❌ Limited (install httpx, aiofiles)"
    except:
        async_status = "❓ Unknown"
    
    print(f"   Async Support: {async_status}")
    print("")
    
    print("💡 Quick Start:")
    print(f"   py-github-analyzer https://github.com/user/repo")
    print(f"   py-github-analyzer https://github.com/user/private-repo -t YOUR_TOKEN")


def check_features():
    """Check and display available features with enhanced information"""
    version_string = safe_get_version()
    
    print(f"🔍 py-github-analyzer v{version_string} Feature Analysis")
    print("=" * 50)
    
    # Core dependencies
    core_deps = {
        'requests': 'HTTP requests and ZIP downloads (required)',
        'rich': 'Beautiful terminal output and logging (required)',
    }
    
    optional_deps = {
        'httpx': 'High-performance async HTTP support (optional)',
        'aiofiles': 'Async file operations for better performance (optional)',
    }
    
    print("\n📦 Core Dependencies:")
    all_core_available = True
    for package, description in core_deps.items():
        try:
            __import__(package)
            print(f"   ✅ {package:12} - {description}")
        except ImportError:
            print(f"   ❌ {package:12} - {description} [NOT INSTALLED]")
            all_core_available = False
    
    print("\n⚡ Performance Dependencies:")
    async_available = True
    for package, description in optional_deps.items():
        try:
            __import__(package)
            print(f"   ✅ {package:12} - {description}")
        except ImportError:
            print(f"   ⚠️  {package:12} - {description} [NOT INSTALLED]")
            async_available = False
    
    print("\n🚀 Access Methods:")
    print("   ✅ ZIP download      - Fast bulk download (primary method)")
    print("   ✅ API method        - File-by-file download (fallback)")
    print("   ✅ Auto selection    - Intelligent ZIP-first strategy")
    
    print("\n📊 Output Formats:")
    print("   ✅ JSON format       - Human-readable (.json)")
    print("   ✅ Binary format     - Compressed for AI (.json.gz)")
    print("   ✅ Both formats      - JSON + Binary output")
    
    print("\n🔐 Authentication & Access:")
    print("   ✅ Public repos      - No authentication required")
    print("   ✅ Private repos     - GitHub token support")
    print("   ✅ Rate limits       - Automatic management (60 → 5000/hr with token)")
    print("   ✅ Smart detection   - Private repository guidance")
    
    print("\n🏆 Performance Features:")
    if async_available:
        print("   ✅ Async mode        - High-performance parallel processing")
        print("   ✅ Concurrent        - Up to 100 simultaneous connections")
        print("   ✅ Batching          - Memory-efficient large repository handling")
    else:
        print("   ⚠️  Async mode        - Install 'httpx aiofiles' for async support")
        print("   ✅ Sync mode         - Standard sequential processing")
    
    print("   ✅ ZIP streaming     - Memory-efficient large file handling")
    print("   ✅ Smart caching     - Optimized repeated operations")
    
    print("\n📈 Analysis Capabilities:")
    print("   ✅ Language detection - Automatic programming language identification")
    print("   ✅ File prioritization - AI-optimized file selection")
    print("   ✅ Metadata generation - Comprehensive repository analysis")
    print("   ✅ Size optimization  - Configurable file and repository limits")
    
    # Overall status
    print("\n🎯 Overall Status:")
    if all_core_available and async_available:
        print("   🟢 EXCELLENT - All features available for maximum performance")
    elif all_core_available:
        print("   🟡 GOOD - Core features available, install async deps for better performance")
    else:
        print("   🔴 LIMITED - Missing core dependencies, please install required packages")
    
    print("\n💡 Installation Commands:")
    if not all_core_available:
        print("   pip install py-github-analyzer  # Install with core dependencies")
    if not async_available:
        print("   pip install httpx aiofiles      # Add async support for better performance")


def show_comprehensive_examples():
    """Show comprehensive usage examples"""
    version_string = safe_get_version()
    
    print(f"📚 py-github-analyzer v{version_string} - Comprehensive Usage Examples")
    print("=" * 60)
    
    examples = """
🚀 BASIC USAGE
==============

1. Analyze Public Repository
   py-github-analyzer https://github.com/user/repo
   
   • Uses optimized ZIP-first strategy
   • Generates compressed binary output (.json.gz)
   • Saves to ./results/ directory

2. Analyze with Custom Output
   py-github-analyzer https://github.com/user/repo -f json -o ./my-results
   
   • Human-readable JSON output
   • Custom output directory
   • Perfect for manual inspection

🔒 PRIVATE REPOSITORY ACCESS
============================

3. Private Repository Analysis
   py-github-analyzer https://github.com/user/private-repo -t ghp_your_token
   
   • Automatic ZIP → API fallback
   • Full private repository access
   • Higher rate limits (5000/hour)

4. Test Private Repository Access
   py-github-analyzer https://github.com/user/private-repo --dry-run -v
   
   • Validates access without downloading
   • Verbose output shows access strategy
   • Helps troubleshoot permission issues

🎯 METHOD SELECTION
===================

5. Force ZIP Method (Fastest)
   py-github-analyzer https://github.com/user/large-repo -m zip
   
   • Best for large public repositories
   • Single download, fast extraction
   • Memory-efficient streaming

6. Force API Method (Most Compatible)
   py-github-analyzer https://github.com/user/repo -m api -t your_token
   
   • File-by-file download
   • Works with rate limits
   • Better for selective analysis

⚡ PERFORMANCE OPTIONS
=====================

7. High-Performance Async Mode (Default)
   py-github-analyzer https://github.com/user/repo -v
   
   • Automatic async detection
   • Parallel processing
   • Best performance for multiple files

8. Compatible Sync Mode
   py-github-analyzer https://github.com/user/repo --sync
   
   • Force synchronous processing
   • Better compatibility
   • Use if async causes issues
"""
    
    print(examples)
    
    print("\n🔑 TOKEN SETUP GUIDE")
    print("=" * 20)
    print("1. Visit: https://github.com/settings/tokens")
    print("2. Click 'Generate new token (classic)'") 
    print("3. Select 'repo' scope for private repository access")
    print("4. Copy token (starts with 'ghp_' or 'github_pat_')")
    print("5. Use: py-github-analyzer [URL] -t YOUR_TOKEN")
    
    print("\n📞 SUPPORT")
    print("=" * 10)
    print("• GitHub: https://github.com/creatorjun/py-github-analyzer")
    print("• Issues: Report bugs and request features")
    print("• Email: createbrain2heart@gmail.com")


def perform_dry_run(args, logger):
    """Perform comprehensive dry run validation"""
    try:
        from .utils import URLParser
        from .github_client import GitHubClient
        
        # Parse URL
        parsed = URLParser.parse_github_url(args.repo_url)
        logger.info(f"🎯 Target Repository: {parsed['owner']}/{parsed['repo']}")
        logger.info(f"🔗 Full URL: {args.repo_url}")
        
        # Show access strategy
        token_status = "✅ Provided" if args.github_token else "❌ Not provided"
        logger.info(f"🔑 GitHub Token: {token_status}")
        
        if args.github_token:
            logger.info("📋 Access Strategy: ZIP download → API fallback (if needed)")
        else:
            logger.info("📋 Access Strategy: ZIP download → Private repo guidance (if private)")
        
        logger.info("")
        logger.info("🔍 Testing repository access...")
        
        with GitHubClient(token=args.github_token) as client:
            try:
                # Test ZIP access first (matches actual strategy)
                logger.info("📦 Testing ZIP download access...")
                zip_available = client._test_zip_availability(parsed['owner'], parsed['repo'], 'main')
                
                if zip_available:
                    logger.info("✅ ZIP download: Accessible")
                    
                    # Get basic repo info
                    repo_info = client.get_repository_info(parsed['owner'], parsed['repo'], safe_mode=True)
                    
                    logger.info("📊 Repository Information:")
                    logger.info(f"   📦 Name: {repo_info['name']}")
                    logger.info(f"   📝 Description: {repo_info.get('description', 'No description')}")
                    logger.info(f"   🗣️  Language: {repo_info.get('language', 'Unknown')}")
                    logger.info(f"   📊 Size: {repo_info.get('size', 0)} KB")
                    logger.info(f"   🌿 Default Branch: {repo_info.get('default_branch', 'Unknown')}")
                    
                    private_status = repo_info.get('private')
                    if private_status is True:
                        logger.info("   🔒 Visibility: Private")
                    elif private_status is False:
                        logger.info("   🌐 Visibility: Public")
                    else:
                        logger.info("   ❓ Visibility: Unknown")
                    
                    logger.info("")
                    logger.info("🎉 Dry run successful! Repository is accessible.")
                    logger.info("💡 Run without --dry-run to perform full analysis.")
                    
                else:
                    logger.warning("⚠️  ZIP download: Not accessible")
                    
                    if args.github_token:
                        logger.info("🔄 Testing API access as fallback...")
                        try:
                            repo_info = client.get_repository_info(parsed['owner'], parsed['repo'], safe_mode=False)
                            logger.info("✅ API access: Successful with token")
                            logger.info("💡 This repository will use API method for analysis.")
                        except Exception as api_error:
                            logger.error(f"❌ API access: Failed - {api_error}")
                            logger.info("🔒 This appears to be a private repository with insufficient token permissions.")
                    else:
                        logger.warning("🔒 Repository appears to be private")
                        logger.info("💡 For private repository access:")
                        logger.info("   1. Get a token: https://github.com/settings/tokens")
                        logger.info("   2. Re-run with: --github-token YOUR_TOKEN")
                
            except Exception as e:
                logger.error(f"❌ Repository access test failed: {e}")
                handle_error(e, args, logger, is_dry_run=True)
                
    except Exception as e:
        logger.error(f"❌ Dry run failed: {e}")
        logger.info("💡 Check your repository URL format and try again.")


async def run_async_analysis(args, logger):
    """Run high-performance asynchronous analysis"""
    logger.info("⚡ Starting high-performance async analysis...")
    
    return await analyze_repository_async(
        repo_url=args.repo_url,
        output_dir=args.output_dir,
        output_format=args.output_format,
        github_token=args.github_token,
        method=args.method
    )


def run_sync_analysis(args, logger):
    """Run synchronous analysis"""
    logger.info("🔄 Starting synchronous analysis...")
    
    return analyze_repository(
        repo_url=args.repo_url,
        output_dir=args.output_dir,
        output_format=args.output_format,
        github_token=args.github_token,
        verbose=args.verbose
    )


def handle_error(error, args, logger, is_dry_run=False):
    """Handle analysis errors with enhanced private repo guidance"""
    error_name = type(error).__name__
    
    # Enhanced private repository handling
    if error_name == 'PrivateRepositoryError':
        logger.error("🔒 Private Repository Detected!")
        logger.info("")
        if not is_dry_run:
            logger.info("This repository requires a GitHub personal access token for access.")
        
        logger.info("📋 Quick Setup Guide:")
        logger.info("   1. Visit: https://github.com/settings/tokens")
        logger.info("   2. Click 'Generate new token (classic)'")
        logger.info("   3. Select 'repo' scope for private repository access") 
        logger.info("   4. Copy the generated token")
        logger.info("   5. Re-run your command with the token")
        logger.info("")
        logger.info("💡 Command with token:")
        logger.info(f"   py-github-analyzer {args.repo_url} --github-token YOUR_TOKEN")
        logger.info("")
        logger.info("🔐 Token formats:")
        logger.info("   • Classic: ghp_xxxxxxxxxxxxxxxxxxxx")
        logger.info("   • Fine-grained: github_pat_xxxxxxxxxx")
        
    elif error_name == 'AuthenticationError':
        logger.error("🔐 GitHub Authentication Issue")
        if "token" in str(error).lower() or "권한" in str(error):
            logger.info("")
            logger.info("Your token may not have the required permissions for private repositories.")
            logger.info("")
            logger.info("🔧 Token Permission Fix:")
            logger.info("   1. Visit: https://github.com/settings/tokens")
            logger.info("   2. Find your existing token")
            logger.info("   3. Edit the token settings")
            logger.info("   4. Ensure 'repo' scope is selected")
            logger.info("   5. Update the token if needed")
            logger.info("")
            logger.info("💡 Alternative: Create a new token with proper scopes")
        else:
            logger.info("")
            logger.info("GitHub authentication failed. Please check your token.")
            logger.info("Get a new token at: https://github.com/settings/tokens")
    
    # ... (rest of error handling remains the same)
    
    # Always show the original error for debugging when verbose
    if args.verbose:
        logger.debug(f"Original error: {error_name}: {error}")


def display_success_summary(result, logger):
    """Display enhanced analysis success summary"""
    metadata = result.get('metadata', {})
    output_paths = result.get('output_paths', {})
    
    logger.info("✅ Analysis completed successfully!")
    logger.info("")
    
    # Repository information
    logger.info("📊 Repository Analysis:")
    logger.info(f"   📦 Repository: {metadata.get('repo', 'Unknown')}")
    logger.info(f"   📁 Files analyzed: {metadata.get('files', 0)}")
    
    try:
        size_value = metadata.get('size', 0)
        if isinstance(size_value, str):
            # Handle string format like "123KB"
            import re
            numbers = re.findall(r'\d+', size_value)
            size_kb = float(numbers[0]) if numbers else 0
        else:
            size_kb = float(size_value) / 1024 if size_value else 0
        logger.info(f"   📏 Total size: {size_kb:.2f} KB")
    except:
        logger.info(f"   📏 Total size: Unknown")
    
    # Language information
    languages = metadata.get('lang', [])
    if languages and languages != ['Unknown']:
        logger.info(f"   🗣️  Primary language: {languages[0]}")
        if len(languages) > 1:
            other_langs = ', '.join(languages[1:3])  # Show up to 3 languages
            more = f" (+{len(languages)-3} more)" if len(languages) > 3 else ""
            logger.info(f"   🌐 Other languages: {other_langs}{more}")
    
    # Additional metadata
    dependencies = metadata.get('deps', 0)
    if dependencies > 0:
        logger.info(f"   📦 Dependencies found: {dependencies}")
    
    logger.info("")
    
    # Output files
    logger.info("💾 Generated Files:")
    for file_type, file_path in output_paths.items():
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            size_kb = file_path_obj.stat().st_size / 1024
            logger.info(f"   📄 {file_type}: {file_path} ({size_kb:.1f} KB)")
        else:
            logger.info(f"   📄 {file_type}: {file_path}")
    
    logger.info("")
    logger.info("🎉 Repository analysis complete! Files are ready for AI processing.")
    
    # Usage suggestions
    if any('json' in path for path in output_paths.values()):
        logger.info("💡 Human-readable data available in JSON files")
    if any('gz' in path for path in output_paths.values()):
        logger.info("🤖 AI-optimized data available in compressed binary files")


if __name__ == '__main__':
    main()
