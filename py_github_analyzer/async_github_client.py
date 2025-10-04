"""

Async GitHub Client for py-github-analyzer v1.0.0

High-performance asynchronous GitHub API interaction with optimized access flow

"""

import asyncio
import time
import zipfile
import json
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import quote
from pathlib import Path

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .config import Config
from .exceptions import (
    NetworkError,
    RateLimitExceededError,
    AuthenticationError,
    RepositoryNotFoundError,
    RepositoryTooLargeError,
    PrivateRepositoryError,
    TimeoutError as AnalyzerTimeoutError,
    handle_github_api_error,
    create_private_repo_guidance_message,
    create_repo_not_found_message
)
from .utils import URLParser, ValidationUtils
from .logger import AnalyzerLogger


class AsyncRateLimitManager:
    """Async-safe GitHub API rate limit management with race condition protection"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.limit = 5000 if token else 60
        self.remaining = self.limit
        self.reset_time = int(time.time()) + 3600
        self._lock = asyncio.Lock()
        self._api_call_lock = asyncio.Lock()  # 전체 API 호출 과정을 보호하는 락

    async def update_from_headers(self, headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        async with self._lock:
            self.limit = int(headers.get('x-ratelimit-limit', self.limit))
            self.remaining = int(headers.get('x-ratelimit-remaining', self.remaining))
            self.reset_time = int(headers.get('x-ratelimit-reset', self.reset_time))

    async def check_rate_limit(self, required_calls: int = 1) -> bool:
        """Check if we have enough API calls remaining"""
        async with self._lock:
            return self.remaining >= (required_calls + Config.RATE_LIMIT_BUFFER)

    async def consume_calls(self, count: int = 1):
        """Consume API calls from remaining count"""
        async with self._lock:
            self.remaining = max(0, self.remaining - count)

    def wait_time_until_reset(self) -> int:
        """Calculate wait time until rate limit resets"""
        return max(0, self.reset_time - int(time.time()))

    async def wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset if necessary"""
        wait_time = self.wait_time_until_reset()
        if wait_time > 0 and self.remaining <= Config.RATE_LIMIT_BUFFER:
            await asyncio.sleep(min(wait_time, 300))  # Max 5 minutes wait

    async def execute_api_call(self, api_call_func, required_calls: int = 1):
        """
        Execute API call with atomic rate limit management
        This prevents race conditions by making the entire check-call-update process atomic
        """
        async with self._api_call_lock:
            # Step 1: Check rate limit
            if not await self.check_rate_limit(required_calls):
                await self.wait_for_rate_limit_reset()
                
                # Re-check after waiting
                if not await self.check_rate_limit(required_calls):
                    raise RateLimitExceededError(
                        "Rate limit still exceeded after waiting",
                        reset_time=self.reset_time,
                        remaining=self.remaining
                    )
            
            # Step 2: Execute API call
            try:
                response = await api_call_func()
                
                # Step 3: Update rate limit info from response headers
                await self.update_from_headers(dict(response.headers))
                await self.consume_calls(required_calls)
                
                return response
                
            except Exception as e:
                # If API call failed, don't consume rate limit calls
                raise e


class AsyncGitHubSession:
    """Async HTTP session for GitHub API using httpx"""
    
    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx library is required for async operations. Install with: pip install httpx")
        
        self.token = token
        self.timeout = timeout
        
        # Setup HTTP headers for GitHub API
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'py-github-analyzer/1.0.0'
        }
        
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        
        # Create httpx client with enhanced connection pooling
        limits = httpx.Limits(
            max_keepalive_connections=50,
            max_connections=200,
            keepalive_expiry=30
        )
        
        timeout_config = httpx.Timeout(timeout)
        
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout_config,
            limits=limits,
            follow_redirects=True
        )

    async def request(self, method: str, url: str, raise_on_error: bool = True, **kwargs) -> httpx.Response:
        """Make async HTTP request with optional error handling"""
        try:
            response = await self.client.request(method, url, **kwargs)
            
            # Handle GitHub API errors only if requested
            if raise_on_error and not response.is_success:
                error_data = None
                try:
                    if response.content:
                        error_data = response.json()
                except:
                    pass
                
                error = handle_github_api_error(response.status_code, error_data, url)
                raise error
            
            return response
        
        except httpx.TimeoutException:
            raise AnalyzerTimeoutError(f"Request timeout after {self.timeout} seconds", self.timeout)
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection error: {e}")
        except httpx.HTTPError as e:
            raise NetworkError(f"HTTP error: {e}")

    async def get(self, url: str, raise_on_error: bool = True, **kwargs) -> httpx.Response:
        """GET request wrapper"""
        return await self.request('GET', url, raise_on_error=raise_on_error, **kwargs)

    async def close(self):
        """Close HTTP session"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AsyncGitHubClient:
    """High-performance async GitHub client with optimized parallel processing"""
    
    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        self.token = token
        self.logger = logger or AnalyzerLogger()
        self.rate_limit_manager = AsyncRateLimitManager(token)
        self.session = None
        self._semaphore = None

    async def __aenter__(self):
        self.session = AsyncGitHubSession(self.token)
        
        # Enhanced concurrency limits based on token availability
        max_concurrent = 100 if self.token else 20
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_repository_info(self, owner: str, repo: str, safe_mode: bool = False) -> Dict[str, Any]:
        """Get basic repository information with safe mode option"""
        url = URLParser.build_api_url(owner, repo, "")
        
        try:
            if safe_mode:
                # Safe mode: don't use rate limit protection for basic info
                response = await self.session.get(url, raise_on_error=False)
                
                if not response.is_success:
                    return {
                        'name': repo,
                        'full_name': f'{owner}/{repo}',
                        'description': '',
                        'language': 'Unknown',
                        'size': 0,
                        'default_branch': 'main',
                        'private': None
                    }
            else:
                # Use atomic rate limit management for API calls
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(url)
                )
            
            repo_data = response.json()
            
            return {
                'name': repo_data['name'],
                'full_name': repo_data['full_name'],
                'description': repo_data.get('description', ''),
                'language': repo_data.get('language', 'Unknown'),
                'size': repo_data.get('size', 0),
                'default_branch': repo_data.get('default_branch', 'main'),
                'private': repo_data.get('private', False),
                'archived': repo_data.get('archived', False),
                'disabled': repo_data.get('disabled', False),
                'topics': repo_data.get('topics', []),
                'license': repo_data.get('license', {}).get('name') if repo_data.get('license') else None,
                'created_at': repo_data.get('created_at'),
                'updated_at': repo_data.get('updated_at'),
                'clone_url': repo_data.get('clone_url'),
                'html_url': repo_data.get('html_url')
            }
        
        except Exception as e:
            if safe_mode:
                self.logger.debug(f"Safe mode: Failed to get repository info: {e}")
                return {
                    'name': repo,
                    'full_name': f'{owner}/{repo}',
                    'description': '',
                    'language': 'Unknown',
                    'size': 0,
                    'default_branch': 'main',
                    'private': None
                }
            else:
                raise

    async def detect_default_branch(self, owner: str, repo: str) -> str:
        """Detect the default branch by testing ZIP availability"""
        # Test common branch names concurrently
        tasks = []
        for branch in Config.DEFAULT_BRANCH_PRIORITY:
            tasks.append(self._test_zip_availability(owner, repo, branch))
        
        # Run all tests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if result is True:  # ZIP test successful
                branch = Config.DEFAULT_BRANCH_PRIORITY[i]
                self.logger.debug(f"Detected default branch via concurrent ZIP test: {branch}")
                return branch
        
        self.logger.debug("Could not detect branch via ZIP, using 'main'")
        return 'main'

    async def _test_zip_availability(self, owner: str, repo: str, branch: str) -> bool:
        """Test if ZIP download is available for given branch"""
        zip_url = URLParser.build_zip_url(owner, repo, branch)
        try:
            response = await self.session.get(
                zip_url,
                raise_on_error=False,
                timeout=10
            )
            return response.status_code in [200, 302]
        except:
            return False

    async def download_repository_zip(self, owner: str, repo: str, branch: str = None) -> List[Dict[str, Any]]:
        """Download repository as ZIP with async streaming"""
        if not branch:
            branch = await self.detect_default_branch(owner, repo)
        
        zip_url = URLParser.build_zip_url(owner, repo, branch)
        
        try:
            self.logger.debug(f"Downloading ZIP from: {zip_url}")
            
            async with self.session.client.stream('GET', zip_url) as response:
                # Handle different response codes
                if response.status_code == 404:
                    # Try alternative branches concurrently
                    alternative_branches = ['main', 'master', 'develop', 'dev']
                    if branch in alternative_branches:
                        alternative_branches.remove(branch)
                    
                    # Test all alternatives concurrently
                    tasks = [
                        self._try_alternative_zip(owner, repo, alt_branch)
                        for alt_branch in alternative_branches
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for i, result in enumerate(results):
                        if isinstance(result, tuple):  # Success: (content, branch)
                            content, successful_branch = result
                            self.logger.debug(f"Found repository with branch: {successful_branch}")
                            return await self._extract_zip_contents_async(content, f"{repo}-{successful_branch}")
                    
                    # All branches failed
                    raise PrivateRepositoryError(
                        f"Repository ZIP not accessible - likely private repository",
                        f"https://github.com/{owner}/{repo}"
                    )
                
                elif response.status_code == 403:
                    raise PrivateRepositoryError(
                        f"Repository access forbidden - private repository",
                        f"https://github.com/{owner}/{repo}"
                    )
                
                elif not response.is_success:
                    raise NetworkError(f"Failed to download ZIP: HTTP {response.status_code}")
                
                # Check content length for size limits
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > Config.MAX_TOTAL_SIZE_MB * 2:
                        raise RepositoryTooLargeError(
                            f"Repository ZIP too large: {size_mb:.1f}MB",
                            size_mb, Config.MAX_TOTAL_SIZE_MB * 2
                        )
                
                # Download content with async streaming and size monitoring
                content = b''
                downloaded = 0
                chunk_size = 8192
                max_size_bytes = Config.MAX_TOTAL_SIZE_MB * 2 * 1024 * 1024  # Convert to bytes
                
                async for chunk in response.aiter_bytes(chunk_size):
                    content += chunk
                    downloaded += len(chunk)
                    
                    # Safety check: Monitor downloaded size even without content-length header
                    if downloaded > max_size_bytes:
                        raise RepositoryTooLargeError(
                            f"Repository ZIP download exceeded size limit: {downloaded / (1024*1024):.1f}MB",
                            downloaded / (1024*1024), Config.MAX_TOTAL_SIZE_MB * 2
                        )
                    
                    # Log progress for large downloads
                    if content_length:
                        progress = (downloaded / int(content_length)) * 100
                        if downloaded % (chunk_size * 100) == 0:
                            self.logger.debug(f"Download progress: {progress:.1f}%")
                
                return await self._extract_zip_contents_async(content, f"{repo}-{branch}")
        
        except (PrivateRepositoryError, RepositoryTooLargeError):
            raise
        except httpx.TimeoutException:
            raise AnalyzerTimeoutError(
                f"ZIP download timeout after {Config.TIMEOUT_CONFIG['zip_timeout']} seconds",
                Config.TIMEOUT_CONFIG['zip_timeout']
            )
        except Exception as e:
            self.logger.debug(f"ZIP download failed: {e}")
            raise NetworkError(f"ZIP download failed: {e}")

    async def _try_alternative_zip(self, owner: str, repo: str, branch: str) -> Optional[Tuple[bytes, str]]:
        """Try downloading ZIP for alternative branch"""
        try:
            zip_url = URLParser.build_zip_url(owner, repo, branch)
            async with self.session.client.stream('GET', zip_url) as response:
                if response.is_success:
                    content = b''
                    async for chunk in response.aiter_bytes(8192):
                        content += chunk
                    return content, branch
            return None
        except:
            return None

    async def _extract_zip_contents_async(self, zip_content: bytes, expected_prefix: str) -> List[Dict[str, Any]]:
        """Extract file information from ZIP content asynchronously"""
        # Run CPU-intensive ZIP extraction in thread pool
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(
            None,
            self._extract_zip_contents_sync,
            zip_content,
            expected_prefix
        )
        return files

    def _extract_zip_contents_sync(self, zip_content: bytes, expected_prefix: str) -> List[Dict[str, Any]]:
        """Synchronous ZIP extraction with safe path handling (runs in thread pool)"""
        files = []
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as zip_file:
                # Step 1: Identify the actual root directory structure
                all_paths = [info.filename for info in zip_file.infolist() if not info.is_dir()]
                if not all_paths:
                    return files

                # Find the common root directory by analyzing all file paths
                root_dirs = set()
                for path in all_paths:
                    if '/' in path:
                        root_dirs.add(path.split('/')[0])
                    else:
                        # File at root level - no common directory
                        root_dirs = set()
                        break

                # Determine the actual repository prefix
                if len(root_dirs) == 1:
                    # All files share a common root directory
                    actual_repo_prefix = list(root_dirs)[0]
                    self.logger.debug(f"Detected actual repository prefix: '{actual_repo_prefix}'")
                else:
                    # Files don't share a common root or are at root level
                    actual_repo_prefix = None
                    self.logger.debug("No common repository prefix detected")

                # Step 2: Process files with safe path handling
                for zip_info in zip_file.infolist():
                    if zip_info.is_dir():
                        continue

                    original_path = zip_info.filename

                    # Safe path normalization
                    if actual_repo_prefix and original_path.startswith(f"{actual_repo_prefix}/"):
                        # Remove the confirmed repository prefix
                        file_path = original_path[len(f"{actual_repo_prefix}/"):]
                    elif actual_repo_prefix and original_path == actual_repo_prefix:
                        # Skip if it's just the root directory
                        continue
                    else:
                        # Keep the original path if no common prefix or doesn't match
                        file_path = original_path

                    # Skip empty paths
                    if not file_path or file_path == '/':
                        continue

                    # Skip excluded directories
                    if any(Config.is_excluded_directory(part) for part in file_path.split('/')):
                        continue

                    # Skip binary files
                    if Config.is_binary_file(file_path):
                        continue

                    try:
                        with zip_file.open(zip_info) as file:
                            content = file.read()
                            if len(content) > Config.MAX_FILE_SIZE_BYTES:
                                continue

                            # Try to decode as text
                            try:
                                text_content = content.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    text_content = content.decode('latin-1')
                                except UnicodeDecodeError:
                                    continue

                            files.append({
                                'path': file_path,
                                'size': len(content),
                                'content': text_content,
                                'priority': Config.get_file_priority(file_path)
                            })

                    except Exception:
                        continue

            return files

        except zipfile.BadZipFile as e:
            raise NetworkError(f"Invalid ZIP file: {e}")
        except Exception as e:
            raise NetworkError(f"ZIP extraction failed: {e}")

    async def get_repository_tree_api(self, owner: str, repo: str, branch: str = None) -> List[Dict[str, Any]]:
        """Get repository file tree using GitHub API with atomic rate limit management"""
        if not branch:
            branch = 'main'
        
        url = URLParser.build_api_url(owner, repo, f"git/trees/{branch}?recursive=1")
        
        try:
            async with self._semaphore:
                # Use atomic API call execution
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(url)
                )
                
                tree_data = response.json()
                files = []
                
                for item in tree_data.get('tree', []):
                    if item['type'] == 'blob':
                        files.append({
                            'path': item['path'],
                            'size': item.get('size', 0),
                            'sha': item['sha'],
                            'url': item.get('url', ''),
                            'download_url': f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{quote(item['path'])}"
                        })
                
                self.logger.debug(f"Retrieved {len(files)} files via API")
                return files
        
        except Exception as e:
            self.logger.error(f"Failed to get repository tree via API: {e}")
            raise

    async def download_single_file(self, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download a single file asynchronously with atomic rate limit management"""
        async with self._semaphore:
            try:
                # Use atomic API call execution to prevent race conditions
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(
                        file_info['download_url'],
                        timeout=Config.TIMEOUT_CONFIG['http_timeout']
                    )
                )
                
                content = response.content
                if len(content) > Config.MAX_FILE_SIZE_BYTES:
                    return None
                
                # Try to decode as text
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text_content = content.decode('latin-1')
                    except UnicodeDecodeError:
                        return None
                
                return {
                    'path': file_info['path'],
                    'size': len(content),
                    'content': text_content,
                    'priority': file_info.get('priority', Config.get_file_priority(file_info['path']))
                }
            
            except Exception as e:
                self.logger.debug(f"Failed to download {file_info['path']}: {e}")
                return None

    async def download_files_concurrently(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced concurrent file downloads with batching"""
        if not files:
            return []
        
        self.logger.debug(f"Starting enhanced async download of {len(files)} files")
        
        # Process files in batches to manage memory and connections
        batch_size = 50 if self.token else 20
        completed_files = []
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            # Create download tasks for this batch
            tasks = [
                asyncio.create_task(self.download_single_file(file_info))
                for file_info in batch
            ]
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process batch results
            for j, result in enumerate(batch_results):
                if isinstance(result, dict) and result:
                    completed_files.append(result)
                elif isinstance(result, Exception):
                    self.logger.debug(f"Download task failed: {result}")
            
            self.logger.debug(f"Completed batch {i//batch_size + 1}/{(len(files) + batch_size - 1)//batch_size}")
        
        self.logger.debug(f"Enhanced async download completed: {len(completed_files)} successful files")
        return completed_files

    async def _try_api_method(self, owner: str, repo: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Try API method for private repository access"""
        self.logger.info("Attempting private repository access via async API...")
        
        try:
            repo_info = await self.get_repository_info(owner, repo, safe_mode=False)
            
            # Check if we have enough rate limit for tree API call
            if not await self.rate_limit_manager.check_rate_limit(10):
                raise RateLimitExceededError(
                    "API rate limit approaching. Please retry later or use ZIP method.",
                    reset_time=self.rate_limit_manager.reset_time,
                    remaining=self.rate_limit_manager.remaining
                )
            
            tree_files = await self.get_repository_tree_api(owner, repo, repo_info.get('default_branch'))
            filtered_files = self._filter_and_prioritize_files(tree_files)
            files = await self.download_files_concurrently(filtered_files)
            
            return files, repo_info
        
        except RateLimitExceededError:
            raise
        except (AuthenticationError, RepositoryNotFoundError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Async API access failed: {e}")

    def _should_try_api_fallback(self, error: Exception) -> bool:
        """Determine if API fallback should be attempted for given error"""
        # Expanded fallback conditions: not just PrivateRepositoryError
        fallback_exceptions = (
            PrivateRepositoryError,
            NetworkError,
            AnalyzerTimeoutError,
            RepositoryTooLargeError  # ZIP too large might work with selective API download
        )
        
        # Don't fallback for certain permanent errors
        no_fallback_exceptions = (
            AuthenticationError,
            RateLimitExceededError,
            RepositoryNotFoundError
        )
        
        # Check if error is a fallback candidate
        if isinstance(error, fallback_exceptions):
            return True
        
        # Don't fallback for permanent errors
        if isinstance(error, no_fallback_exceptions):
            return False
        
        # For generic exceptions, check if they might be transient
        error_message = str(error).lower()
        transient_indicators = [
            'timeout',
            'connection',
            'network',
            'temporary',
            'rate limit',
            'server error',
            'service unavailable'
        ]
        
        return any(indicator in error_message for indicator in transient_indicators)

    async def analyze_repository(self, owner: str, repo: str, method: str = "auto") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Optimized async analysis: ZIP first, then enhanced token-aware fallback strategy
        
        Args:
            owner: Repository owner username
            repo: Repository name
            method: Analysis method ('auto', 'zip', 'api')
        
        Returns:
            Tuple of (files, repo_info)
        """
        self.logger.debug(f"Starting async analysis: {owner}/{repo} (token: {'available' if self.token else 'not available'})")
        
        zip_error = None
        
        # Step 1: Always try ZIP download first (async)
        try:
            self.logger.debug("Attempting async ZIP download...")
            files = await self.download_repository_zip(owner, repo)
            repo_info = await self.get_repository_info(owner, repo, safe_mode=True)
            self.logger.info(f"Async ZIP download successful! ({len(files)} files)")
            return files, repo_info
        
        except Exception as e:
            zip_error = e
            self.logger.debug(f"ZIP download failed: {type(e).__name__}: {e}")
        
        # Step 2: Enhanced fallback logic with token availability
        if self.token and zip_error and self._should_try_api_fallback(zip_error):
            self.logger.warning(f"ZIP failed ({type(zip_error).__name__}), attempting API fallback...")
            
            try:
                return await self._try_api_method(owner, repo)
            
            except RateLimitExceededError as e:
                reset_minutes = (e.reset_time - int(time.time())) // 60 if e.reset_time else 0
                self.logger.warning(f"API rate limit exceeded! Retry available in {reset_minutes} minutes.")
                self.logger.info("Please wait for rate limit reset or try with a different token.")
                raise
            
            except AuthenticationError as e:
                self.logger.error("Token permission insufficient or repository access denied")
                self.logger.info("Please verify that your token has 'repo' scope access.")
                raise
            
            except Exception as api_error:
                self.logger.warning(f"API fallback also failed: {type(api_error).__name__}: {api_error}")
                # Re-raise the original ZIP error if API fallback fails
                raise zip_error
        
        # Step 3: Handle specific error cases
        if isinstance(zip_error, PrivateRepositoryError):
            if self.token:
                # Token available but API fallback failed, re-raise the original error
                raise zip_error
            else:
                self.logger.error("Private repository detected.")
                self.logger.info("GitHub token required for private repository access.")
                message = create_private_repo_guidance_message(owner, repo, has_token=False)
                raise PrivateRepositoryError(message, f"https://github.com/{owner}/{repo}")
        
        elif isinstance(zip_error, RepositoryNotFoundError):
            self.logger.error(f"Repository not found: {owner}/{repo}")
            raise zip_error
        
        elif isinstance(zip_error, NetworkError):
            self.logger.error(f"Network error during repository access: {zip_error}")
            raise zip_error
        
        else:
            # Generic error handling
            self.logger.error(f"Repository analysis failed: {type(zip_error).__name__}: {zip_error}")
            
            # Try to get safe repository info for error response
            try:
                repo_info = await self.get_repository_info(owner, repo, safe_mode=True)
            except:
                repo_info = {
                    'name': repo,
                    'full_name': f'{owner}/{repo}',
                    'description': '',
                    'language': 'Unknown',
                    'size': 0,
                    'default_branch': 'main',
                    'private': None
                }
            
            return [], repo_info

    def _filter_and_prioritize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and prioritize files for download"""
        # Add priority to all files first
        for file_info in files:
            file_info['priority'] = Config.get_file_priority(file_info['path'])
        
        filtered_files = []
        for file_info in files:
            path = file_info['path']
            
            # Skip excluded directories
            if any(Config.is_excluded_directory(part) for part in path.split('/')):
                continue
            
            # Skip binary files
            if Config.is_binary_file(path):
                continue
            
            # Skip files that are too large
            if file_info.get('size', 0) > Config.MAX_FILE_SIZE_BYTES:
                continue
            
            filtered_files.append(file_info)
        
        # Sort by priority (highest first)
        filtered_files.sort(key=lambda x: x['priority'], reverse=True)
        
        # Limit total size
        total_size = 0
        selected_files = []
        
        for file_info in filtered_files:
            file_size = file_info.get('size', 0)
            if total_size + file_size <= Config.MAX_TOTAL_SIZE_BYTES:
                selected_files.append(file_info)
                total_size += file_size
            else:
                break
        
        self.logger.debug(f"Selected {len(selected_files)} files out of {len(files)} total")
        return selected_files

    async def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information"""
        return {
            'limit': self.rate_limit_manager.limit,
            'remaining': self.rate_limit_manager.remaining,
            'reset_time': self.rate_limit_manager.reset_time,
            'reset_in_seconds': self.rate_limit_manager.wait_time_until_reset()
        }


# Main user API: Global function
async def analyze_repository_async(
    repo_url: str,
    output_dir: str = "./results",
    output_format: str = "bin",
    github_token: Optional[str] = None,
    method: str = "auto",
    verbose: bool = False,
    dry_run: bool = False,
    fallback: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Enhanced async convenience function for repository analysis
    
    High-performance parallel processing with advanced error handling
    
    User-friendly API: Simple function call for all features
    
    Args:
        repo_url: GitHub repository URL
        output_dir: Output directory path
        output_format: Output format ('json', 'bin', 'both')
        github_token: GitHub access token
        method: Analysis method ('auto', 'zip', 'api')
        verbose: Enable verbose logging
        dry_run: Dry run mode (no output files)
        fallback: Enable fallback strategies
        **kwargs: Additional options
    
    Returns:
        Dict: Analysis results with metadata, files, and output paths
    
    Example:
        # Basic usage
        result = await analyze_repository_async("https://github.com/user/repo")
        
        # Advanced usage
        result = await analyze_repository_async(
            "https://github.com/user/repo",
            output_dir="./my_results",
            github_token="ghp_xxxxxxxxxxxx",
            verbose=True
        )
    """
    # Local imports to avoid circular dependencies
    from .file_processor import FileProcessor
    from .metadata_generator import MetadataGenerator
    from .utils import FileUtils, CompressionUtils
    
    try:
        parsed_url = URLParser.parse_github_url(repo_url)
        owner, repo = parsed_url['owner'], parsed_url['repo']
        
        # Create logger with appropriate verbosity
        logger = AnalyzerLogger(verbose=verbose)
        
        async with AsyncGitHubClient(github_token, logger=logger) as client:
            files, repo_info = await client.analyze_repository(owner, repo, method)
            
            # Skip file processing and output in dry_run mode
            if dry_run:
                return {
                    'metadata': {},
                    'compact_metadata': {},
                    'files': files,
                    'repo_info': repo_info,
                    'processing_metadata': {},
                    'output_paths': {},
                    'success': True,
                    'dry_run': True
                }
            
            # Process files synchronously (CPU-bound operations)
            file_processor = FileProcessor()
            processed_files, processing_metadata = file_processor.process_files(files)
            
            metadata_generator = MetadataGenerator()
            metadata = metadata_generator.generate_metadata(
                processed_files, processing_metadata, repo_info, repo_url
            )
            
            compact_metadata = metadata_generator.generate_compact_metadata(
                processed_files, processing_metadata, repo_info, repo_url
            )
            
            # Create output directory structure
            base_output_dir = Path(output_dir)
            repo_output_dir = base_output_dir / f"{owner}_{repo}"
            FileUtils.ensure_directory(repo_output_dir)
            
            base_filename = f"{owner}_{repo}"
            output_paths = {}
            
            # Save metadata files in JSON format
            meta_path = repo_output_dir / f"{base_filename}_meta.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            output_paths['metadata'] = str(meta_path)
            
            compact_meta_path = repo_output_dir / f"{base_filename}_compact_meta.json"
            with open(compact_meta_path, 'w', encoding='utf-8') as f:
                json.dump(compact_metadata, f, ensure_ascii=False, separators=(',', ':'))
            output_paths['compact_metadata'] = str(compact_meta_path)
            
            # Create optimized code data structure for AI processing
            code_data = {"f": {}}
            for file_info in processed_files:
                path = file_info.get('path', '')
                content = file_info.get('content', '')
                if path and content:
                    code_data["f"][path] = content
            
            # Save based on output format preference
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
            
            return {
                'metadata': metadata,
                'compact_metadata': compact_metadata,
                'files': processed_files,
                'repo_info': repo_info,
                'processing_metadata': processing_metadata,
                'output_paths': output_paths,
                'success': True
            }
    
    except Exception as e:
        return {
            'metadata': {},
            'compact_metadata': {},
            'files': [],
            'repo_info': {},
            'processing_metadata': {},
            'output_paths': {},
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
