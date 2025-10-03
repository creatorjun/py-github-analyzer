"""
GitHub Repository Analyzer Core Module
Enhanced with empty repository detection and user-friendly error messages
Version: 1.0.0
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from threading import Lock

from .config import Config
from .utils import URLParser, CompressionUtils, FileUtils
from .logger import get_logger, AnalyzerLogger
from .exceptions import (
    GitHubAnalyzerError,
    RepositoryNotFoundError,
    AuthenticationError,
    RepositoryTooLargeError,
    ValidationError,
    UnsupportedFormatError,
    OutputError
)

from .github_client import GitHubClient
from .metadata_generator import MetadataGenerator
from .file_processor import FileProcessor

# Async client import
try:
    from .async_github_client import AsyncGitHubClient
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    AsyncGitHubClient = None

# Fix variable name consistency
ASYNC_CLIENT_AVAILABLE = ASYNC_AVAILABLE

class EmptyRepositoryError(GitHubAnalyzerError):
    """Raised when repository exists but contains no analyzable files"""
    
    def __init__(self, message: str, repo_url: str, file_count: int = 0):
        super().__init__(message)
        self.repo_url = repo_url
        self.file_count = file_count

class RepositoryContentError(GitHubAnalyzerError):
    """Raised when repository content cannot be analyzed"""
    
    def __init__(self, message: str, repo_url: str, reason: str):
        super().__init__(message)
        self.repo_url = repo_url
        self.reason = reason

class GitHubRepositoryAnalyzer:
    """Main analysis class for GitHub repositories"""
    
    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        self.token = token
        self.logger = logger or get_logger()
        self._lock = Lock()
        self._client = None

    def analyze_repository(
        self,
        repo_url: str,
        output_dir: str = "./results",
        output_format: str = "bin",
        github_token: Optional[str] = None,
        method: str = "auto",
        verbose: bool = False,
        dry_run: bool = False,
        fallback: bool = True,
        async_mode: bool = True  # Default to async mode
    ) -> Dict[str, Any]:
        """
        Main analysis method with all options.
        If async_mode=True, uses AsyncGitHubClient with asyncio event loop.
        """
        if async_mode and ASYNC_CLIENT_AVAILABLE:
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        self.logger.warning("⚠️ Already in event loop, using sync mode...")
                        return self._analyze_repository_sync(
                            repo_url, output_dir, output_format, github_token, method, verbose, dry_run, fallback
                        )
                except RuntimeError:
                    # No running loop, we can use asyncio.run()
                    pass
                
                return asyncio.run(
                    self._analyze_repository_async(
                        repo_url, output_dir, output_format, github_token, method, verbose, dry_run, fallback
                    )
                )
            except Exception as e:
                if fallback:
                    self.logger.warning(f"⚠️ Primary async analysis failed: {e}. Attempting fallback...")
                    return self._analyze_repository_sync(
                        repo_url, output_dir, output_format, github_token, method, verbose, dry_run, fallback
                    )
                else:
                    raise
        else:
            if async_mode and not ASYNC_CLIENT_AVAILABLE:
                self.logger.warning("Async mode requested but async client not available, using sync mode")
            return self._analyze_repository_sync(
                repo_url, output_dir, output_format, github_token, method, verbose, dry_run, fallback
            )

    def _analyze_repository_sync(
        self,
        repo_url: str,
        output_dir: str,
        output_format: str,
        github_token: Optional[str],
        method: str,
        verbose: bool,
        dry_run: bool,
        fallback: bool
    ) -> Dict[str, Any]:
        """Synchronous repository analysis"""
        
        # Use provided token or instance token
        active_token = github_token or self.token
        
        # Parse and validate URL
        try:
            parsed_url = URLParser.parse_github_url(repo_url)
            owner = parsed_url['owner']
            repo = parsed_url['repo']
        except ValidationError as e:
            raise ValidationError(f"Invalid repository URL: {e}")
        
        # Validate output format
        if output_format not in Config.OUTPUT_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported output format: {output_format}",
                output_format,
                Config.OUTPUT_FORMATS
            )
        
        # Dry run handling
        if dry_run:
            self.logger.info("Dry-run mode: Simulating repository analysis")
            return self._simulate_dry_run(owner, repo, output_dir, output_format)
        
        # Perform actual analysis
        try:
            with GitHubClient(active_token, self.logger) as client:
                self._client = client
                
                # Get repository information
                repo_info = client.get_repository_info(owner, repo)
                
                # Check repository accessibility and constraints
                self._validate_repository_access(repo_info, active_token)
                
                # Analyze repository files
                files, repo_data = client.analyze_repository(owner, repo, method)
                
                # Validate analysis results for empty repositories
                self._validate_analysis_results(files, repo_url, repo_data)
                
                # Process files
                file_processor = FileProcessor(self.logger)
                processed_files, processing_metadata = file_processor.process_files(files)
                
                # Generate metadata
                metadata_generator = MetadataGenerator(self.logger)
                metadata = metadata_generator.generate_metadata(
                    processed_files, processing_metadata, repo_data, repo_url
                )
                
                compact_metadata = metadata_generator.generate_compact_metadata(
                    processed_files, processing_metadata, repo_data, repo_url
                )
                
                # Save results
                output_paths = self._save_results(
                    processed_files, metadata, compact_metadata,
                    owner, repo, output_dir, output_format
                )
                
                # Generate summary
                self._print_analysis_summary(processed_files, metadata, processing_metadata)
                
                # Return consistent structure
                return {
                    'metadata': metadata,
                    'compact_metadata': compact_metadata,
                    'files': processed_files,
                    'repo_info': repo_data,
                    'processing_metadata': processing_metadata,
                    'output_paths': output_paths,
                    'success': True
                }
                
        except (EmptyRepositoryError, RepositoryContentError) as e:
            # Handle empty repositories gracefully
            self.logger.info(str(e))
            return self._create_empty_repository_result(repo_url, output_dir, output_format, str(e))
            
        except Exception as e:
            if fallback:
                self.logger.warning(f"⚠️ Primary sync analysis failed: {e}. Attempting fallback...")
                return self._fallback_analysis(repo_url, output_dir, output_format, active_token)
            else:
                raise

    async def _analyze_repository_async(
        self,
        repo_url: str,
        output_dir: str,
        output_format: str,
        github_token: Optional[str],
        method: str,
        verbose: bool,
        dry_run: bool,
        fallback: bool
    ) -> Dict[str, Any]:
        """Asynchronous repository analysis"""
        
        active_token = github_token or self.token
        
        # Parse and validate URL
        try:
            parsed_url = URLParser.parse_github_url(repo_url)
            owner = parsed_url['owner']
            repo = parsed_url['repo']
        except ValidationError as e:
            raise ValidationError(f"Invalid repository URL: {e}")
        
        # Validate output format
        if output_format not in Config.OUTPUT_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported output format: {output_format}",
                output_format,
                Config.OUTPUT_FORMATS
            )
        
        # Dry run handling
        if dry_run:
            self.logger.info("Dry-run mode: Simulating repository analysis")
            return self._simulate_dry_run(owner, repo, output_dir, output_format)
        
        # Perform async analysis
        try:
            async with AsyncGitHubClient(active_token, self.logger) as client:
                self._client = client
                
                # Get repository information
                repo_info = await client.get_repository_info(owner, repo)
                
                # Check repository accessibility and constraints
                self._validate_repository_access(repo_info, active_token)
                
                # Analyze repository files
                files, repo_data = await client.analyze_repository(owner, repo, method)
                
                # Validate analysis results for empty repositories
                self._validate_analysis_results(files, repo_url, repo_data)
                
                # Process files (sync part)
                file_processor = FileProcessor(self.logger)
                processed_files, processing_metadata = file_processor.process_files(files)
                
                # Generate metadata (sync part)
                metadata_generator = MetadataGenerator(self.logger)
                metadata = metadata_generator.generate_metadata(
                    processed_files, processing_metadata, repo_data, repo_url
                )
                
                compact_metadata = metadata_generator.generate_compact_metadata(
                    processed_files, processing_metadata, repo_data, repo_url
                )
                
                # Save results
                output_paths = self._save_results(
                    processed_files, metadata, compact_metadata,
                    owner, repo, output_dir, output_format
                )
                
                # Generate summary
                self._print_analysis_summary(processed_files, metadata, processing_metadata)
                
                # Return consistent structure
                return {
                    'metadata': metadata,
                    'compact_metadata': compact_metadata,
                    'files': processed_files,
                    'repo_info': repo_data,
                    'processing_metadata': processing_metadata,
                    'output_paths': output_paths,
                    'success': True
                }
                
        except (EmptyRepositoryError, RepositoryContentError) as e:
            # Handle empty repositories gracefully
            self.logger.info(str(e))
            return self._create_empty_repository_result(repo_url, output_dir, output_format, str(e))
            
        except Exception as e:
            if fallback:
                self.logger.warning(f"Async analysis failed: {e}. Falling back to sync mode...")
                return self._analyze_repository_sync(
                    repo_url, output_dir, output_format, github_token, method, verbose, dry_run, fallback
                )
            else:
                raise

    def _validate_analysis_results(self, files: List[Dict[str, Any]], repo_url: str, repo_info: Dict[str, Any]):
        """Validate analysis results and provide helpful user messages"""
        
        if not files or len(files) == 0:
            repo_name = repo_info.get('full_name', repo_url)
            
            # 저장소가 완전히 비어있는 경우
            if repo_info.get('size', 0) == 0:
                raise EmptyRepositoryError(
                    f"🌟 Repository '{repo_name}' is empty!\n\n"
                    f"💡 This repository exists but contains no files yet.\n"
                    f"   • This often happens with newly created repositories\n"  
                    f"   • Try again after the owner adds some code\n"
                    f"   • Or try analyzing a different repository with actual content\n\n"
                    f"✨ Suggested repositories to try:\n"
                    f"   • https://github.com/octocat/Hello-World (minimal example)\n"
                    f"   • https://github.com/microsoft/vscode (large project)\n"
                    f"   • https://github.com/python/cpython (Python source code)",
                    repo_url,
                    0
                )
            
            # 파일은 있지만 분석 가능한 파일이 없는 경우
            else:
                raise RepositoryContentError(
                    f"📁 Repository '{repo_name}' contains no analyzable code files!\n\n"
                    f"💡 This repository exists but has no code files we can analyze.\n"
                    f"   • Repository size: {repo_info.get('size', 0)}KB\n"
                    f"   • Possible reasons:\n"
                    f"     - Only binary files (images, executables, etc.)\n"
                    f"     - Only documentation files\n"
                    f"     - Files are too large (over {Config.MAX_FILE_SIZE_BYTES // 1024}KB each)\n"
                    f"     - All files in excluded directories (.git, node_modules, etc.)\n\n"
                    f"✨ Try a repository with source code files like:\n"
                    f"   • .py, .js, .java, .cpp, .go, .rs files\n"
                    f"   • README.md, package.json, requirements.txt",
                    repo_url,
                    "no_analyzable_files"
                )

    def _create_empty_repository_result(self, repo_url: str, output_dir: str, output_format: str, message: str) -> Dict[str, Any]:
        """Create result for empty or non-analyzable repositories"""
        
        try:
            parsed_url = URLParser.parse_github_url(repo_url)
            owner, repo = parsed_url['owner'], parsed_url['repo']
        except:
            owner, repo = "unknown", "unknown"
        
        # 기본 메타데이터
        empty_metadata = {
            'repo': f'{owner}/{repo}',
            'desc': 'Empty repository - no analyzable files found',
            'lang': ['None'],
            'size': '0KB',
            'files': 0,
            'main': [],
            'deps': [],
            'created': int(time.time()),
            'version': Config.VERSION,
            'analysis_mode': 'empty_repository',
            'user_message': message
        }
        
        # 출력 파일 생성
        output_paths = self._save_results([], empty_metadata, empty_metadata, owner, repo, output_dir, output_format)
        
        return {
            'metadata': empty_metadata,
            'compact_metadata': empty_metadata, 
            'files': [],
            'repo_info': {'name': repo, 'full_name': f'{owner}/{repo}', 'empty': True},
            'output_paths': output_paths,
            'success': True,
            'empty_repository': True,
            'user_friendly_message': message
        }

    def analyze(self, repo_url: str, output_format: str = "bin") -> Dict[str, Any]:
        """Simplified analysis method for backward compatibility"""
        return self.analyze_repository(repo_url, output_format=output_format)

    def _validate_repository_access(self, repo_info: Dict[str, Any], token: Optional[str]):
        """Validate repository access and constraints"""
        
        # Check if private repository requires token
        if repo_info.get('private', False) and not token:
            raise AuthenticationError("Private repository requires GitHub token")
        
        # Check if repository is accessible
        if repo_info.get('disabled', False):
            raise RepositoryNotFoundError("Repository is disabled")
        
        # Warn about archived repositories
        if repo_info.get('archived', False):
            self.logger.warning("Repository is archived and may be outdated")
        
        # Check size constraints
        repo_size_kb = repo_info.get('size', 0)
        if repo_size_kb > (Config.MAX_TOTAL_SIZE_MB * 1024 * 10):  # 10x limit for repo size
            raise RepositoryTooLargeError(
                "Repository is too large for analysis",
                repo_size_kb / 1024,
                Config.MAX_TOTAL_SIZE_MB * 10
            )

    def _save_results(
        self,
        files: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        compact_metadata: Dict[str, Any],
        owner: str,
        repo: str,
        output_dir: str,
        output_format: str
    ) -> Dict[str, str]:
        """Save analysis results to files"""
        
        try:
            # Create output directory
            base_output_dir = Path(output_dir)
            repo_output_dir = base_output_dir / f"{owner}_{repo}"
            FileUtils.ensure_directory(repo_output_dir)
            
            # Prepare file paths
            base_filename = f"{owner}_{repo}"
            
            # Create code data structure (AI-optimized)
            code_data = {"f": {}}  # Minimal key for AI parsing
            for file_info in files:
                path = file_info.get('path', '')
                content = file_info.get('content', '')
                if path and content:
                    code_data["f"][path] = content
            
            output_paths = {}
            
            # Save metadata (always JSON)
            meta_path = repo_output_dir / f"{base_filename}_meta.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            output_paths['metadata'] = str(meta_path)
            
            # Save compact metadata
            compact_meta_path = repo_output_dir / f"{base_filename}_compact_meta.json"
            with open(compact_meta_path, 'w', encoding='utf-8') as f:
                json.dump(compact_metadata, f, ensure_ascii=False, separators=(',', ':'))
            output_paths['compact_metadata'] = str(compact_meta_path)
            
            # Save code data based on format
            if output_format in ["json", "both"]:
                code_json_path = repo_output_dir / f"{base_filename}_code.json"
                with open(code_json_path, 'w', encoding='utf-8') as f:
                    json.dump(code_data, f, ensure_ascii=False, separators=(',', ':'))
                output_paths['code_json'] = str(code_json_path)
            
            if output_format in ["bin", "both"]:
                code_bin_path = repo_output_dir / f"{base_filename}_code.json.gz"
                json_str = json.dumps(code_data, ensure_ascii=False, separators=(',', ':'))
                compressed_data = CompressionUtils.compress_data(json_str, "gzip")
                with open(code_bin_path, 'wb') as f:
                    f.write(compressed_data)
                output_paths['code_binary'] = str(code_bin_path)
            
            self.logger.success(f"Results saved to: {repo_output_dir}")
            return output_paths
            
        except Exception as e:
            raise OutputError(f"Failed to save results: {e}")

    def _simulate_dry_run(self, owner: str, repo: str, output_dir: str, output_format: str) -> Dict[str, Any]:
        """Simulate analysis for dry-run mode"""
        
        self.logger.info(f"Simulating analysis for {owner}/{repo}")
        
        # Simulate some processing time
        time.sleep(0.5)
        
        # Create expected output paths
        base_output_dir = Path(output_dir)
        repo_output_dir = base_output_dir / f"{owner}_{repo}"
        base_filename = f"{owner}_{repo}"
        
        simulated_paths = {
            'metadata': str(repo_output_dir / f"{base_filename}_meta.json"),
            'compact_metadata': str(repo_output_dir / f"{base_filename}_compact_meta.json")
        }
        
        if output_format in ["json", "both"]:
            simulated_paths['code_json'] = str(repo_output_dir / f"{base_filename}_code.json")
        if output_format in ["bin", "both"]:
            simulated_paths['code_binary'] = str(repo_output_dir / f"{base_filename}_code.json.gz")
        
        # Return consistent structure
        return {
            'metadata': {'repo': f'{owner}/{repo}', 'dry_run': True},
            'files': [],
            'output_paths': simulated_paths,
            'success': True,
            'dry_run': True
        }

    def _fallback_analysis(self, repo_url: str, output_dir: str, output_format: str, token: Optional[str]) -> Dict[str, Any]:
        """Fallback analysis with minimal functionality"""
        
        self.logger.warning("⚠️ Using fallback analysis mode...")
        
        try:
            parsed_url = URLParser.parse_github_url(repo_url)
            owner, repo = parsed_url['owner'], parsed_url['repo']
            
            with GitHubClient(token, self.logger) as client:
                # Get basic repository info only
                try:
                    repo_info = client.get_repository_info(owner, repo)
                except Exception as e:
                    self.logger.error(f"❌ Failed to get repository info: {e}")
                    repo_info = {
                        'name': repo,
                        'full_name': f'{owner}/{repo}',
                        'description': 'Repository information unavailable',
                        'language': 'Unknown',
                        'size': 0
                    }
                
                # Create output directory
                base_output_dir = Path(output_dir)
                repo_output_dir = base_output_dir / f"{owner}_{repo}"
                FileUtils.ensure_directory(repo_output_dir)
                base_filename = f"{owner}_{repo}"
                output_paths = {}
                
                # Create minimal metadata
                minimal_metadata = {
                    'repo': f"{owner}/{repo}",
                    'desc': repo_info.get('description', 'Repository analysis (fallback mode)'),
                    'lang': [repo_info.get('language', 'Unknown')] if repo_info.get('language') else ['Unknown'],
                    'size': f"{repo_info.get('size', 0)}KB",
                    'files': 0,
                    'main': [],
                    'deps': [],
                    'fallback_mode': True,
                    'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Create compact metadata
                compact_metadata = {
                    'repo': f"{owner}/{repo}",
                    'lang': minimal_metadata['lang'],
                    'size': minimal_metadata['size'],
                    'files': 0,
                    'main': [],
                    'deps': [],
                    'fallback': True
                }
                
                # Save metadata files
                meta_path = repo_output_dir / f"{base_filename}_meta.json"
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(minimal_metadata, f, ensure_ascii=False, indent=2)
                output_paths['metadata'] = str(meta_path)
                
                compact_meta_path = repo_output_dir / f"{base_filename}_compact_meta.json"
                with open(compact_meta_path, 'w', encoding='utf-8') as f:
                    json.dump(compact_metadata, f, ensure_ascii=False, separators=(',', ':'))
                output_paths['compact_metadata'] = str(compact_meta_path)
                
                # Create empty code structure for fallback
                empty_code_data = {"f": {}}
                
                # Save code files based on format
                if output_format in ["json", "both"]:
                    code_json_path = repo_output_dir / f"{base_filename}_code.json"
                    with open(code_json_path, 'w', encoding='utf-8') as f:
                        json.dump(empty_code_data, f, ensure_ascii=False, separators=(',', ':'))
                    output_paths['code_json'] = str(code_json_path)
                
                if output_format in ["bin", "both"]:
                    code_bin_path = repo_output_dir / f"{base_filename}_code.json.gz"
                    json_str = json.dumps(empty_code_data, ensure_ascii=False, separators=(',', ':'))
                    compressed_data = CompressionUtils.compress_data(json_str, "gzip")
                    with open(code_bin_path, 'wb') as f:
                        f.write(compressed_data)
                    output_paths['code_binary'] = str(code_bin_path)
                
                self.logger.warning("⚠️ Fallback analysis completed - limited data available")
                
                return {
                    'metadata': minimal_metadata,
                    'compact_metadata': compact_metadata,
                    'files': [],
                    'repo_info': repo_info,
                    'output_paths': output_paths,
                    'success': True,
                    'fallback_mode': True,
                    'processing_metadata': {
                        'fallback_mode': True,
                        'download_method': 'fallback',
                        'processing_time': time.time()
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Even fallback analysis failed: {e}")
            raise GitHubAnalyzerError(f"Complete analysis failure: {e}")

    def _print_analysis_summary(self, files: List[Dict[str, Any]], metadata: Dict[str, Any], processing_metadata: Dict[str, Any]):
        """Print analysis summary"""
        
        try:
            total_files = len(files)
            total_size = sum(f.get('size', 0) for f in files if f.get('size'))
            total_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
            
            languages = metadata.get('lang', [])
            main_language = languages[0] if languages else 'Unknown'
            dependencies = metadata.get('deps', [])
            main_files = metadata.get('main', [])
            frameworks = metadata.get('frameworks', [])
            
            self.logger.info("📊 Analysis Summary:")
            self.logger.info(f" Repository: {metadata.get('repo', 'Unknown')}")
            self.logger.info(f" Files: {total_files}")
            self.logger.info(f" Size: {total_size_mb:.2f} MB")
            self.logger.info(f" Primary Language: {main_language}")
            
            if languages:
                self.logger.info(f" Languages: {', '.join(languages[:3])}")
            if dependencies:
                self.logger.info(f" Dependencies: {len(dependencies)}")
            if frameworks:
                self.logger.info(f" Frameworks: {', '.join(frameworks[:2])}")
            if main_files:
                self.logger.info(f" Entry Points: {', '.join(main_files[:2])}")
            
            processing_method = processing_metadata.get('download_method', 'Unknown')
            self.logger.info(f" Method Used: {processing_method}")
            
        except Exception as e:
            self.logger.warning(f"Failed to print summary: {e}")

    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get current rate limit information"""
        if self._client:
            return self._client.get_rate_limit_info()
        return None

    # Additional async method for direct async usage
    async def analyze_repository_async(
        self,
        repo_url: str,
        output_dir: str = "./results",
        output_format: str = "bin",
        github_token: Optional[str] = None,
        method: str = "auto",
        verbose: bool = False,
        dry_run: bool = False,
        fallback: bool = True
    ) -> Dict[str, Any]:
        """Direct async analysis method"""
        if not ASYNC_AVAILABLE:
            raise GitHubAnalyzerError("Async functionality not available. Install httpx and aiofiles.")
        
        return await self._analyze_repository_async(
            repo_url, output_dir, output_format, github_token, method, verbose, dry_run, fallback
        )


# Convenience function for simple usage
def analyze_repository(
    repo_url: str,
    output_dir: str = "./results",
    output_format: str = "bin",
    github_token: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Convenience function for simple repository analysis"""
    
    analyzer = GitHubRepositoryAnalyzer(token=github_token)
    
    if verbose:
        from .logger import set_verbose
        set_verbose(True)
    
    return analyzer.analyze_repository(
        repo_url=repo_url,
        output_dir=output_dir,
        output_format=output_format,
        verbose=verbose
    )


# Async convenience function
async def analyze_repository_async(
    repo_url: str,
    output_dir: str = "./results",
    output_format: str = "bin",
    github_token: Optional[str] = None,
    method: str = "auto",
    verbose: bool = False
) -> Dict[str, Any]:
    """Async convenience function for repository analysis"""
    
    analyzer = GitHubRepositoryAnalyzer(token=github_token)
    
    if verbose:
        from .logger import set_verbose
        set_verbose(True)
    
    return await analyzer.analyze_repository_async(
        repo_url=repo_url,
        output_dir=output_dir,
        output_format=output_format,
        github_token=github_token,
        method=method,
        verbose=verbose
    )
