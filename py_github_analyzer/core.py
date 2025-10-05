#!/usr/bin/env python3

"""

GitHub Repository Analyzer Core Module

High-performance async-first GitHub repository analysis with enhanced error reporting

"""

import asyncio
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from .async_github_client import AsyncGitHubClient
from .config import Config
from .exceptions import TimeoutError as AnalyzerTimeoutError
from .exceptions import *
from .file_processor import FileProcessor
from .logger import AnalyzerLogger, get_logger
from .metadata_generator import MetadataGenerator
from .utils import TokenUtils, URLParser


class EmptyRepositoryError(GitHubAnalyzerError):
    """Raised when repository exists but contains no analyzable files"""

    pass


class GitHubRepositoryAnalyzer:
    """High-performance async GitHub repository analyzer with enhanced error handling"""
    
    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        """Initialize analyzer with optional token and logger"""
        # 🔧 이 부분을 다음과 같이 수정:
        self._github_token = self._resolve_github_token(token)
        self.logger = logger or get_logger()
        
        # Initialize components
        self.client = AsyncGitHubClient(self._github_token, self.logger)
        self.metadata_generator = MetadataGenerator()
        self.file_processor = FileProcessor(self.logger)
        
        # 토큰 정보 로깅
        self._log_initialization_info()

    def _resolve_github_token(self, provided_token: Optional[str]) -> Optional[str]:
        """Resolve GitHub token from multiple sources"""
        try:
            from .utils import TokenUtils
            return TokenUtils.get_github_token(provided_token)
        except ImportError:
            # Fallback if TokenUtils is not available
            if provided_token:
                return provided_token
            import os
            return os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')

    def _log_initialization_info(self):
        """Log initialization information"""
        if self._github_token:
            try:
                from .utils import TokenUtils
                token_info = TokenUtils.get_token_info(self._github_token)
                if token_info['status'] == 'provided':
                    self.logger.info(f"🔑 GitHub token loaded: {token_info['masked']} ({token_info['type']})")
                else:
                    self.logger.info("🔑 GitHub token loaded: provided")
            except (ImportError, Exception):
                self.logger.info("🔑 GitHub token: provided")
            self.logger.info("⚡ Rate limit: 5000 requests/hour")
        else:
            self.logger.warning("⚠️  No GitHub token - rate limited to 60 requests/hour")

    @property
    def github_token(self) -> Optional[str]:
        """Get the current GitHub token"""
        return self._github_token

    @property 
    def token(self) -> Optional[str]:
        """Backward compatibility property"""
        return self._github_token

    async def analyze_repository_async(
        self,
        repo_url: str,
        output_dir: str = "./results",
        output_format: str = "both",
        method: str = "auto",
        verbose: bool = False,
        dry_run: bool = False,
        fallback: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analyze a GitHub repository asynchronously with ZIP-first strategy and comprehensive error handling

        Args:
            repo_url: GitHub repository URL
            output_dir: Output directory for results
            output_format: Output format ('json', 'bin', or 'both')
            method: Analysis method ('auto', 'api', or 'zip')
            verbose: Enable verbose logging
            dry_run: Simulate analysis without actual processing
            fallback: Enable fallback mode on errors

        Returns:
            Dict containing analysis results with detailed error information
        """
        original_error = None
        fallback_error = None

        try:
            url_info = URLParser.parse_github_url(repo_url)
            owner = url_info["owner"]
            repo = url_info["repo"]

            if verbose:
                self.logger.info(f"ℹ️ 📂 Analyzing repository: {owner}/{repo}")
                self.logger.info(f"ℹ️ 🎯 Method: {method}")
                self.logger.info(f"ℹ️ 📁 Output: {output_dir}")
                self.logger.info(f"ℹ️ 📄 Format: {output_format}")

            if dry_run:
                self.logger.info(f"ℹ️ 🏃 Dry-run mode: Simulating analysis...")
                return {
                    "success": True,
                    "dry_run": True,
                    "repository": f"{owner}/{repo}",
                    "metadata": {
                        "repo": f"{owner}/{repo}",
                        "owner": owner,
                        "name": repo,
                        "lang": ["Simulated"],
                        "size": "Unknown",
                    },
                    "files": [],
                    "output_paths": {},
                    "fallback_mode": False,
                }

            # ZIP-FIRST STRATEGY: Always try ZIP first, regardless of token availability
            files = []
            repo_info = {}

            if method == "api":
                # Explicit API-only mode
                self.logger.info("🔧 Using API-only mode (explicit)")
                files, repo_info = await self.client.analyze_repository(
                    owner, repo, method="api"
                )

            elif method == "zip":
                # Explicit ZIP-only mode
                self.logger.info("📦 Using ZIP-only mode (explicit)")
                files, repo_info = await self.client.analyze_repository(
                    owner, repo, method="zip"
                )

            else:
                # Auto mode: ZIP-first strategy (optimal for performance and rate limits)
                self.logger.info("🎯 Using ZIP-first strategy (auto mode)")

                try:
                    # Step 1: Always try ZIP first - faster and rate limit friendly
                    self.logger.debug("📦 Attempting ZIP download...")
                    files, repo_info = await self.client.analyze_repository(
                        owner, repo, method="auto"
                    )

                    if files:
                        self.logger.info(
                            f"✅ ZIP download successful! ({len(files)} files)"
                        )
                    else:
                        self.logger.warning("⚠️ ZIP download returned no files")

                except PrivateRepositoryError as e:
                    # Private repository - try API if token available
                    if self.token:
                        self.logger.warning(
                            f"🔐 Private repository detected, trying API with token..."
                        )
                        try:
                            files, repo_info = await self.client.analyze_repository(
                                owner, repo, method="api"
                            )
                            self.logger.info(
                                f"✅ API access successful! ({len(files)} files)"
                            )
                        except Exception as api_error:
                            self.logger.error(f"❌ API access also failed: {api_error}")
                            raise e  # Re-raise original private repo error
                    else:
                        self.logger.error("❌ Private repository requires GitHub token")
                        raise e

                except (
                    NetworkError,
                    AnalyzerTimeoutError,
                    RepositoryTooLargeError,
                ) as e:
                    # Network/timeout issues - try API as fallback if token available
                    if self.token:
                        self.logger.warning(
                            f"⚠️ ZIP failed ({type(e).__name__}), trying API fallback..."
                        )
                        try:
                            files, repo_info = await self.client.analyze_repository(
                                owner, repo, method="api"
                            )
                            self.logger.info(
                                f"✅ API fallback successful! ({len(files)} files)"
                            )
                        except Exception as api_error:
                            self.logger.error(
                                f"❌ API fallback also failed: {api_error}"
                            )
                            raise e  # Re-raise original error
                    else:
                        self.logger.error(
                            f"❌ ZIP failed and no token for API fallback: {e}"
                        )
                        raise e

                except Exception as e:
                    # Other errors - still try API fallback if available
                    if self.token:
                        self.logger.warning(
                            f"⚠️ ZIP failed with unexpected error, trying API fallback: {e}"
                        )
                        try:
                            files, repo_info = await self.client.analyze_repository(
                                owner, repo, method="api"
                            )
                            self.logger.info(
                                f"✅ API fallback successful! ({len(files)} files)"
                            )
                        except Exception as api_error:
                            self.logger.error(
                                f"❌ API fallback also failed: {api_error}"
                            )
                            raise e  # Re-raise original error
                    else:
                        raise e

            if not files:
                self.logger.warning(f"⚠️ No files extracted from repository: {repo_url}")
                if fallback:
                    self.logger.warning("⚠️ Using fallback analysis mode...")
                    return await self._fallback_analysis(
                        owner, repo, output_dir, output_format
                    )
                else:
                    raise EmptyRepositoryError(
                        f"No files found in repository: {owner}/{repo}"
                    )

            # Process files using thread pool for CPU-intensive work
            processed_files, processing_metadata = await asyncio.to_thread(
                self.file_processor.process_files, files
            )

            if not processed_files:
                self.logger.warning("⚠️ No valid files to process")
                if fallback:
                    return await self._fallback_analysis(
                        owner, repo, output_dir, output_format
                    )
                else:
                    raise EmptyRepositoryError("No processable files found")

            # Generate metadata using thread pool
            metadata = await asyncio.to_thread(
                self.metadata_generator.generate_metadata,
                processed_files,
                processing_metadata,
                repo_info,
                repo_url,
            )

            total_lines = sum(
                f.get("lines", 0) for f in processed_files if isinstance(f, dict)
            )
            self.logger.info(
                f"✅ Analysis completed: {len(processed_files)} files, {total_lines:,} lines"
            )
            self.logger.info(
                f"🗣️ Primary language: {metadata.get('lang', ['Unknown'])[0] if metadata.get('lang') else 'Unknown'}"
            )

            # Save output files
            output_paths = await self._save_output_async(
                output_dir, output_format, metadata, processed_files, f"{owner}_{repo}"
            )

            return {
                "success": True,
                "repository": f"{owner}/{repo}",
                "metadata": metadata,
                "files": processed_files,
                "output_paths": output_paths,
                "fallback_mode": False,
                "analysis_method": method,
                "token_used": bool(self.token),
            }

        except Exception as e:
            # Store the original error for comprehensive reporting
            original_error = e
            self.logger.error(f"❌ Analysis failed with error: {type(e).__name__}: {e}")

            if fallback:
                self.logger.warning("⚠️ Attempting fallback analysis...")
                try:
                    url_info = URLParser.parse_github_url(repo_url)
                    fallback_result = await self._fallback_analysis(
                        url_info["owner"],
                        url_info["repo"],
                        output_dir,
                        output_format,
                        original_error_info={
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "analysis_method": method,
                        },
                    )

                    if fallback_result.get("success"):
                        # Fallback succeeded - include original error info for context
                        fallback_result["original_error"] = {
                            "type": type(original_error).__name__,
                            "message": str(original_error),
                            "fallback_triggered": True,
                        }
                        return fallback_result
                    else:
                        # Fallback also failed - this info is already in fallback_result
                        return fallback_result

                except Exception as fallback_ex:
                    # Store fallback error for comprehensive reporting
                    fallback_error = fallback_ex
                    self.logger.error(
                        f"❌ Fallback analysis also failed: {type(fallback_ex).__name__}: {fallback_ex}"
                    )

                    # Create comprehensive error message with both failures
                    comprehensive_error = self._create_comprehensive_error_message(
                        original_error, fallback_error
                    )

                    return {
                        "success": False,
                        "error_message": comprehensive_error,
                        "original_error": {
                            "type": type(original_error).__name__,
                            "message": str(original_error),
                        },
                        "fallback_error": {
                            "type": type(fallback_error).__name__,
                            "message": str(fallback_error),
                        },
                        "repository": repo_url,
                        "fallback_mode": True,
                        "analysis_method": method,
                        "token_available": bool(self.token),
                        "error_context": {
                            "both_attempts_failed": True,
                            "fallback_attempted": True,
                        },
                    }
            else:
                # No fallback attempted
                return {
                    "success": False,
                    "error_message": f"Analysis failed: {type(original_error).__name__}: {original_error}",
                    "error_type": type(original_error).__name__,
                    "repository": repo_url,
                    "fallback_mode": False,
                    "analysis_method": method,
                    "token_available": bool(self.token),
                    "error_context": {"fallback_attempted": False},
                }

    def _create_comprehensive_error_message(
        self, original_error: Exception, fallback_error: Exception
    ) -> str:
        """Create a comprehensive error message that includes both original and fallback failures"""
        original_type = type(original_error).__name__
        fallback_type = type(fallback_error).__name__

        # Create detailed error message
        comprehensive_message = (
            f"Repository analysis failed completely. "
            f"Primary analysis failed with {original_type}: {original_error}. "
            f"Fallback analysis also failed with {fallback_type}: {fallback_error}."
        )

        # Add helpful context based on error types
        if isinstance(original_error, (PrivateRepositoryError, AuthenticationError)):
            if not self.token:
                comprehensive_message += (
                    " Consider providing a GitHub token for private repository access."
                )
            else:
                comprehensive_message += " Verify that your GitHub token has sufficient permissions (repo scope)."

        elif isinstance(original_error, (NetworkError, AnalyzerTimeoutError)):
            comprehensive_message += " This appears to be a network connectivity issue. Please check your internet connection and try again."

        elif isinstance(original_error, RateLimitExceededError):
            comprehensive_message += " GitHub API rate limit exceeded. Please wait before retrying or use a different token."

        elif isinstance(original_error, RepositoryTooLargeError):
            comprehensive_message += " Repository is too large for analysis. Consider analyzing a smaller repository or increasing size limits."

        return comprehensive_message

    async def _fallback_analysis(
        self,
        owner: str,
        repo: str,
        output_dir: str,
        output_format: str,
        original_error_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Provide basic fallback analysis when normal processing fails"""
        try:
            # Try to get basic repository info
            async with self.client:
                repo_info = await self.client.get_repository_info(
                    owner, repo, safe_mode=True
                )

            fallback_metadata = {
                "repo": f"{owner}/{repo}",
                "owner": owner,
                "name": repo,
                "description": repo_info.get("description", "No description available"),
                "lang": ["Unknown"],
                "size": repo_info.get("size", 0),
                "created": repo_info.get("created_at", "Unknown"),
                "updated": repo_info.get("updated_at", "Unknown"),
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
                "fallback_mode": True,
                "analysis_mode": "basic_metadata_only",
            }

            # Include original error info if provided
            if original_error_info:
                fallback_metadata["original_failure"] = original_error_info

            output_paths = await self._save_output_async(
                output_dir,
                output_format,
                fallback_metadata,
                [],
                f"{owner}_{repo}_fallback",
            )

            self.logger.warning("⚠️ Fallback analysis completed with limited data")
            return {
                "success": True,
                "repository": f"{owner}/{repo}",
                "metadata": fallback_metadata,
                "files": [],
                "output_paths": output_paths,
                "fallback_mode": True,
                "analysis_method": "fallback",
                "original_error": original_error_info,
                "warning": "Analysis completed in fallback mode with limited repository information only",
            }

        except Exception as e:
            fallback_error_message = (
                f"Fallback analysis failed: {type(e).__name__}: {e}"
            )
            self.logger.error(f"❌ {fallback_error_message}")

            # Create detailed fallback failure response
            error_details = {
                "success": False,
                "error_message": fallback_error_message,
                "fallback_error": {"type": type(e).__name__, "message": str(e)},
                "repository": f"{owner}/{repo}",
                "fallback_mode": True,
                "analysis_method": "fallback_failed",
            }

            # Include original error info if available
            if original_error_info:
                error_details["original_error"] = original_error_info
                comprehensive_msg = (
                    f"Complete analysis failure. "
                    f"Original error: {original_error_info.get('error_type', 'Unknown')}: {original_error_info.get('error_message', 'Unknown')}. "
                    f"Fallback error: {type(e).__name__}: {e}"
                )
                error_details["error_message"] = comprehensive_msg

            return error_details

    async def _save_output_async(
        self,
        output_dir: str,
        output_format: str,
        metadata: Dict[str, Any],
        files: List[Dict[str, Any]],
        filename_prefix: str,
    ) -> Dict[str, str]:
        """Save analysis results asynchronously with enhanced error handling"""
        try:
            output_dir_path = Path(output_dir)
            output_dir_path.mkdir(parents=True, exist_ok=True)

            output_paths = {}

            if output_format in ["json", "both"]:
                json_path = output_dir_path / f"{filename_prefix}.json"
                output_data = {
                    "metadata": metadata,
                    "files": files,
                    "generated_at": asyncio.get_event_loop().time(),
                    "version": Config.VERSION,
                }

                async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(output_data, indent=2, ensure_ascii=False))
                output_paths["json"] = str(json_path)
                self.logger.debug(f"Saved JSON output: {json_path}")

            if output_format in ["bin", "both"]:
                bin_path = output_dir_path / f"{filename_prefix}.bin"
                output_data = {
                    "metadata": metadata,
                    "files": files,
                    "generated_at": asyncio.get_event_loop().time(),
                    "version": Config.VERSION,
                }

                async with aiofiles.open(bin_path, "wb") as f:
                    import pickle

                    await f.write(pickle.dumps(output_data))
                output_paths["bin"] = str(bin_path)
                self.logger.debug(f"Saved binary output: {bin_path}")

            return output_paths

        except Exception as e:
            self.logger.error(f"❌ Failed to save output files: {e}")
            return {"error": f"Output save failed: {e}"}


# Standalone async function for repository analysis
async def analyze_repository_async(repo_url: str, **kwargs) -> Dict[str, Any]:
    """
    Standalone async function for repository analysis with enhanced error reporting

    Args:
        repo_url: GitHub repository URL
        **kwargs: Additional arguments passed to GitHubRepositoryAnalyzer

    Returns:
        Dict: Analysis results with comprehensive error information
    """
    analyzer = GitHubRepositoryAnalyzer(
        token=kwargs.get("github_token"), logger=kwargs.get("logger")
    )

    return await analyzer.analyze_repository_async(repo_url, **kwargs)
