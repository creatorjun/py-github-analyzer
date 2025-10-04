"""
Command Line Interface for py-github-analyzer v1.0.0
High-performance async GitHub repository analyzer CLI
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Windows UTF-8 encoding setup
if os.name == 'nt':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSFSENCODING'] = '0'
    os.environ['PYTHONUTF8'] = '1'
    
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            pass
    
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass
    
    try:
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
    except:
        pass

from .core import analyze_repository_async
from .config import Config
from .logger import set_verbose, get_logger
from .exceptions import GitHubAnalyzerError, ValidationError
from .utils import TokenUtils

def create_argument_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        prog="py-github-analyzer",
        description="High-performance async GitHub repository analyzer",
        epilog="Example: py-github-analyzer https://github.com/user/repo --output ./results\n\n"
               "GitHub Token Priority (highest to lowest):\n"
               "1. --github-token parameter\n" 
               "2. GITHUB_TOKEN environment variable\n"
               "3. GH_TOKEN environment variable\n"
               "4. Anonymous access (rate limited)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "url",
        help="GitHub repository URL"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./results",
        help="Output directory (default: ./results)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["json", "bin", "both"],
        default="both",
        help="Output format (default: both)"
    )
    
    parser.add_argument(
        "-t", "--github-token",
        help="GitHub personal access token (or set GITHUB_TOKEN/GH_TOKEN env var)"
    )
    
    parser.add_argument(
        "-m", "--method",
        choices=["auto", "api", "zip"],
        default="auto",
        help="Analysis method (default: auto)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate analysis without actual processing"
    )
    
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback mode on errors"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"py-github-analyzer {Config.VERSION}"
    )
    
    return parser

def print_banner():
    """Print application banner"""
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        py-github-analyzer v{Config.VERSION}                          ║
║                   High-Performance Async GitHub Analyzer                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

def print_analysis_info(args):
    """Print analysis configuration info"""
    logger = get_logger()
    logger.info(f"Repository: {args.url}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Output format: {args.format}")
    logger.info(f"Analysis method: {args.method}")
    
    # Auto-detect token and show detailed info
    active_token = TokenUtils.get_github_token(args.github_token)
    token_info = TokenUtils.get_token_info(active_token)
    
    if token_info['status'] == 'provided':
        source = "parameter" if args.github_token else "environment"
        status_msg = f"{token_info['masked']} ({token_info['type']}, from {source})"
        
        if token_info['valid']:
            logger.info(f"GitHub token: {status_msg}")
            logger.info("Rate limit: 5000 requests/hour (authenticated)")
        else:
            logger.warning(f"GitHub token: {status_msg}")
            logger.warning("Token format may be invalid - please check your token")
    else:
        logger.info("GitHub token: Not provided (anonymous access)")
        logger.warning("Rate limit: 60 requests/hour without token")
        logger.info("To increase rate limit, set GITHUB_TOKEN environment variable")
    
    if args.dry_run:
        logger.info("Mode: Dry-run (simulation)")
    
    print()

def print_results_summary(result):
    """Print analysis results summary"""
    logger = get_logger()
    
    if result.get('success'):
        metadata = result.get('metadata', {})
        files = result.get('files', [])
        
        print("\n" + "="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        
        logger.info(f"Repository: {metadata.get('repo', 'Unknown')}")
        
        languages = metadata.get('lang', [])
        if languages:
            if isinstance(languages, list) and len(languages) > 0:
                logger.info(f"Primary language: {languages[0]}")
            else:
                logger.info(f"Primary language: {languages}")
        
        logger.info(f"Total files analyzed: {len(files)}")
        logger.info(f"Repository size: {metadata.get('size', 'Unknown')}")
        
        deps = metadata.get('deps', [])
        if deps:
            logger.info(f"Dependencies found: {len(deps)}")
        
        # Show total lines of code
        total_lines = sum(f.get('lines', 0) for f in files if isinstance(f, dict))
        if total_lines > 0:
            logger.info(f"Total lines of code: {total_lines:,}")
        
        output_paths = result.get('output_paths', {})
        if output_paths:
            print("\nOutput files:")
            for output_type, path in output_paths.items():
                if path:
                    print(f"  {output_type}: {path}")
        
        if result.get('fallback_mode'):
            print("\n⚠️  Analysis completed in fallback mode (limited information)")
            if 'error_message' in result:
                logger.warning(f"Original error: {result['error_message']}")
        else:
            print("\n✅ Analysis completed successfully")
            
    else:
        print("\n❌ Analysis failed")
        if 'error_message' in result:
            logger.error(f"Error: {result['error_message']}")

def print_token_help():
    """Print token setup help"""
    print("\n" + "="*80)
    print("GITHUB TOKEN SETUP")
    print("="*80)
    print("For private repositories or higher rate limits:")
    print("1. Visit: https://github.com/settings/tokens")
    print("2. Click 'Generate new token (classic)'")
    print("3. Select 'repo' scope for private repository access")
    print("4. Copy the generated token")
    print("5. Set environment variable:")
    print("   export GITHUB_TOKEN=your_token_here")
    print("   # or")
    print("   export GH_TOKEN=your_token_here")
    print("6. Or use --github-token parameter")

async def async_main():
    """Main async entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if args.verbose:
        set_verbose(True)
    
    logger = get_logger()
    
    try:
        print_banner()
        print_analysis_info(args)
        
        # Check for token if accessing potentially private repo
        active_token = TokenUtils.get_github_token(args.github_token)
        if not active_token and ('private' in args.url.lower() or args.verbose):
            print_token_help()
            print()
        
        result = await analyze_repository_async(
            repo_url=args.url,
            output_dir=args.output,
            output_format=args.format,
            github_token=args.github_token,
            method=args.method,
            verbose=args.verbose,
            dry_run=args.dry_run,
            fallback=not args.no_fallback
        )
        
        print_results_summary(result)
        
        if result.get('success'):
            # Success with potential warnings
            if result.get('fallback_mode'):
                return 2  # Success with warnings
            else:
                return 0  # Complete success
        else:
            return 1  # Failure
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        print_token_help()
        return 1
    except GitHubAnalyzerError as e:
        logger.error(f"Analysis error: {e}")
        if "private" in str(e).lower() or "authentication" in str(e).lower():
            print_token_help()
        return 1
    except KeyboardInterrupt:
        logger.warning("Analysis interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

def main():
    """Main entry point for CLI"""
    try:
        if sys.platform == 'win32':
            # Windows specific async loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
