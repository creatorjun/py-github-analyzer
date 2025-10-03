"""
GitHub Client for py-github-analyzer v1.0.0
Enhanced synchronous GitHub API and ZIP downloading client
"""

import time
import zipfile
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import quote
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import requests with fallback
try:
    import requests
    from requests.adapters import HTTPAdapter
    REQUESTS_AVAILABLE = True
    
    # Try to import Retry class from different locations
    Retry = None
    try:
        from urllib3.util.retry import Retry
    except ImportError:
        try:
            from urllib3.util import Retry
        except ImportError:
            try:
                import urllib3
                Retry = urllib3.util.retry.Retry
            except (ImportError, AttributeError):
                Retry = None
                
except ImportError:
    REQUESTS_AVAILABLE = False
    Retry = None

from .config import Config
from .exceptions import (
    NetworkError, 
    RateLimitExceededError, 
    AuthenticationError, 
    RepositoryTooLargeError,
    RepositoryNotFoundError,
    PrivateRepositoryError,
    TimeoutError as AnalyzerTimeoutError,
    handle_github_api_error
)
from .utils import URLParser, RetryUtils, FileUtils, ValidationUtils
from .logger import AnalyzerLogger


class RateLimitManager:
    """GitHub API rate limit management"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.limit = 5000 if token else 60
        self.remaining = self.limit
        self.reset_time = int(time.time()) + 3600
        self._lock = threading.Lock()

    def update_from_headers(self, headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        with self._lock:
            self.limit = int(headers.get('X-RateLimit-Limit', self.limit))
            self.remaining = int(headers.get('X-RateLimit-Remaining', self.remaining))
            self.reset_time = int(headers.get('X-RateLimit-Reset', self.reset_time))

    def check_rate_limit(self, required_calls: int = 1) -> bool:
        """Check if we have enough API calls remaining"""
        with self._lock:
            return self.remaining >= (required_calls + Config.RATE_LIMIT_BUFFER)

    def consume_calls(self, count: int = 1):
        """Consume API calls from remaining count"""
        with self._lock:
            self.remaining = max(0, self.remaining - count)

    def wait_time_until_reset(self) -> int:
        """Calculate wait time until rate limit resets"""
        return max(0, self.reset_time - int(time.time()))

    def suggest_method(self, estimated_files: int) -> str:
        """Suggest best method based on rate limit"""
        if not self.check_rate_limit(estimated_files):
            return "zip"  # Not enough API calls, use ZIP
        return "api" if self.token else "zip"  # Prefer API if we have token and calls


class GitHubSession:
    """Enhanced requests session for GitHub API"""
    
    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required but not installed")
        
        self.session = requests.Session()
        self.token = token
        self.timeout = timeout

        # Setup retry strategy if Retry class is available
        if Retry is not None:
            try:
                # Try newer parameter name first
                retry_strategy = Retry(
                    total=3,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["HEAD", "GET", "OPTIONS"],
                    backoff_factor=1
                )
            except TypeError:
                try:
                    # Try newer parameter name first
                    retry_strategy = Retry(
                        total=3,
                        status_forcelist=[429, 500, 502, 503, 504],
                        method_whitelist=["HEAD", "GET", "OPTIONS"],
                        backoff_factor=1
                    )
                except TypeError:
                    try:
                        # Fallback to older parameter name
                        retry_strategy = Retry(
                            total=3,
                            status_forcelist=[429, 500, 502, 503, 504],
                            backoff_factor=1
                        )
                    except TypeError:
                        retry_strategy = None
            
            if retry_strategy:
                adapter = HTTPAdapter(max_retries=retry_strategy)
                self.session.mount("http://", adapter)
                self.session.mount("https://", adapter)

        # Setup headers
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'{Config.PACKAGE_NAME}/{Config.VERSION}'
        }
        
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        
        self.session.headers.update(headers)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            if not response.ok:
                error = handle_github_api_error(response.status_code, 
                                              response.json() if response.content else None)
                raise error
            
            return response
            
        except requests.exceptions.Timeout:
            raise AnalyzerTimeoutError(f"Request timeout after {self.timeout} seconds", self.timeout)
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {e}")

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request"""
        return self.request('GET', url, **kwargs)

    def close(self):
        """Close session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class GitHubClient:
    """Main GitHub API and ZIP client"""
    
    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        self.token = token
        self.logger = logger or AnalyzerLogger()
        self.rate_limit_manager = RateLimitManager(token)
        self.session = None

    def __enter__(self):
        self.session = GitHubSession(self.token)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()

    def get_repository_info(self, owner: str, repo: str, safe_mode: bool = False) -> Dict[str, Any]:
        """Get basic repository information"""
        url = URLParser.build_api_url(owner, repo, "")
        
        try:
            response = self.session.get(url)
            self.rate_limit_manager.update_from_headers(response.headers)
            self.rate_limit_manager.consume_calls(1)
            
            repo_data = response.json()
            
            return {
                'name': repo_data['name'],
                'full_name': repo_data['full_name'],
                'description': repo_data.get('description', ''),
                'language': repo_data.get('language', 'Unknown'),
                'size': repo_data.get('size', 0),  # Size in KB
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
                self.logger.debug(f"Failed to get repository info: {e}")
                # Return minimal info for fallback
                return {
                    'name': repo,
                    'full_name': f'{owner}/{repo}',
                    'description': '',
                    'language': 'Unknown',
                    'size': 0,
                    'default_branch': 'main',
                    'private': False
                }
            else:
                error_message = str(e)
                if any(keyword in error_message.lower() for keyword in ['not found', '404']):
                    # Check if it's actually private vs non-existent
                    if self.token:
                        raise RepositoryNotFoundError(f"Repository {owner}/{repo} not found or you don't have access")
                    else:
                        raise PrivateRepositoryError(f"Repository {owner}/{repo} appears to be private or doesn't exist. Private repositories require a GitHub token.")
                elif any(keyword in error_message.lower() for keyword in ['private', 'authentication', '403']):
                    raise AuthenticationError("Repository not found, private, or requires authentication.\nPlease verify the repository URL and access permissions.")
                else:
                    raise NetworkError(f"Failed to get repository info: {e}")

    def _test_zip_availability(self, owner: str, repo: str, branch: str) -> bool:
        """Test if ZIP download is available for repository)"""
        zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
        
        try:
            # Use HEAD request to test availability without downloading
            response = self.session.session.head(
                zip_url,
                timeout=10,
                allow_redirects=True,
                headers={
                    'Accept': 'application/zip, application/octet-stream, */*',
                    'User-Agent': f'{Config.PACKAGE_NAME}/{Config.VERSION}'
                }
            )
            
            # ZIP is available if we get 200 and proper content type
            content_type = response.headers.get('content-type', '')
            return (response.status_code == 200 and 
                    ('zip' in content_type.lower() or 
                     'octet-stream' in content_type.lower() or
                     'application' in content_type.lower()))
                     
        except Exception as e:
            self.logger.debug(f"ZIP availability test failed: {e}")
            return False

    def detect_default_branch(self, owner: str, repo: str) -> str:
        """Detect the default branch of repository"""
        
        # Try repository info first
        try:
            repo_info = self.get_repository_info(owner, repo, safe_mode=True)
            if repo_info.get('default_branch'):
                return repo_info['default_branch']
        except:
            pass
        
        # Fallback: try common branch names
        for branch in Config.DEFAULT_BRANCH_PRIORITY:
            try:
                url = URLParser.build_api_url(owner, repo, f"branches/{branch}")
                response = self.session.get(url)
                self.rate_limit_manager.update_from_headers(response.headers)
                self.rate_limit_manager.consume_calls(1)
                
                if response.ok:
                    self.logger.debug(f"Detected default branch: {branch}")
                    return branch
            except:
                continue
        
        self.logger.warning("Could not detect default branch, using 'main'")
        return "main"

    def download_repository_zip(self, owner: str, repo: str, branch: str = None) -> List[Dict[str, Any]]:
        """Download repository as ZIP and extract file information - FIXED for better reliability"""
        
        if not branch:
            branch = self.detect_default_branch(owner, repo)
        
        # Try multiple branch possibilities
        possible_branches = [branch]
        if branch == 'main':
            possible_branches.append('master')
        elif branch == 'master':
            possible_branches.append('main')
        
        last_error = None
        
        for attempt_branch in possible_branches:
            zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{attempt_branch}"
            
            try:
                self.logger.debug(f"Attempting ZIP download from {zip_url}")
                
                headers = {
                    'Accept': 'application/zip, application/octet-stream, */*',
                    'User-Agent': f'{Config.PACKAGE_NAME}/{Config.VERSION}',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
                
                response = self.session.session.get(
                    zip_url,
                    timeout=Config.TIMEOUT_CONFIG['zip_timeout'],
                    stream=True,
                    allow_redirects=True,
                    headers=headers
                )
                
                if response.status_code == 404:
                    self.logger.debug(f"Branch {attempt_branch} not found (404)")
                    continue
                elif response.status_code == 403:
                    raise PrivateRepositoryError(f"Repository {owner}/{repo} appears to be private")
                elif not response.ok:
                    raise NetworkError(f"ZIP download failed with status {response.status_code}")
                
                # Verify content is actually a ZIP file
                content_type = response.headers.get('content-type', '')
                if not any(ct in content_type.lower() for ct in ['zip', 'octet-stream', 'application']):
                    self.logger.warning(f"Unexpected content-type: {content_type}")
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / 1024 / 1024
                    if size_mb > Config.MAX_TOTAL_SIZE_MB * 2:  # Allow 2x limit for ZIP
                        raise RepositoryTooLargeError(
                            f"Repository ZIP too large: {size_mb:.1f}MB",
                            size_mb,
                            Config.MAX_TOTAL_SIZE_MB * 2
                        )
                
                # Download content in chunks
                content = b''
                downloaded = 0
                chunk_size = 8192
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive chunks
                        content += chunk
                        downloaded += len(chunk)
                        
                        # Progress update for large downloads
                        if content_length and (downloaded % (chunk_size * 100) == 0):
                            progress = (downloaded / int(content_length)) * 100
                            self.logger.debug(f"Download progress: {progress:.1f}%")
                
                # Verify we got valid ZIP content
                if len(content) < 100:  # ZIP files should be at least 100 bytes
                    raise NetworkError(f"ZIP file too small: {len(content)} bytes")
                
                if not content.startswith(b'PK'):
                    raise NetworkError("Downloaded content is not a valid ZIP file (missing ZIP signature)")
                
                self.logger.debug(f"ZIP download successful: {len(content)} bytes")
                return self._extract_zip_contents(content, f"{repo}-{attempt_branch}")
                
            except requests.exceptions.RequestException as e:
                last_error = e
                self.logger.debug(f"ZIP download failed for branch {attempt_branch}: {e}")
                continue
            except (NetworkError, RepositoryTooLargeError) as e:
                last_error = e
                self.logger.debug(f"ZIP processing failed for branch {attempt_branch}: {e}")
                continue
            except Exception as e:
                last_error = e
                self.logger.debug(f"Unexpected error for branch {attempt_branch}: {e}")
                continue
        
        # If all branches failed, raise appropriate error
        if isinstance(last_error, (PrivateRepositoryError, AuthenticationError)):
            raise last_error
        else:
            raise NetworkError(f"Failed to download ZIP for any branch {possible_branches}. Last error: {last_error}")

    def _extract_zip_contents(self, zip_content: bytes, expected_prefix: str) -> List[Dict[str, Any]]:
        """Extract file information from ZIP content"""
        files = []
        
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as zip_file:
                for zip_info in zip_file.infolist():
                    if zip_info.is_dir():
                        continue
                    
                    file_path = zip_info.filename
                    
                    # Remove the repository prefix from path
                    if file_path.startswith(f"{expected_prefix}/"):
                        file_path = file_path[len(f"{expected_prefix}/"):]
                    elif "/" in file_path:
                        # Handle different branch name format
                        file_path = "/".join(file_path.split("/")[1:])
                    
                    if not file_path:  # Skip root files with no path
                        continue
                    
                    # Skip excluded directories and binary files
                    if any(Config.is_excluded_directory(part) for part in file_path.split("/")):
                        continue
                    
                    if Config.is_binary_file(file_path):
                        continue
                    
                    # Skip large files
                    if zip_info.file_size > Config.MAX_FILE_SIZE_BYTES:
                        self.logger.debug(f"Skipping large file: {file_path} ({zip_info.file_size} bytes)")
                        continue
                    
                    try:
                        with zip_file.open(zip_info) as file:
                            content = file.read()
                        
                        # Try to decode as text
                        try:
                            text_content = content.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                text_content = content.decode('latin-1')
                            except UnicodeDecodeError:
                                self.logger.debug(f"Skipping binary file: {file_path}")
                                continue
                        
                        files.append({
                            'path': file_path,
                            'size': len(content),
                            'content': text_content,
                            'priority': Config.get_file_priority(file_path)
                        })
                        
                    except Exception as e:
                        self.logger.debug(f"Error reading file {file_path}: {e}")
                        continue
            
            self.logger.debug(f"Extracted {len(files)} files from ZIP")
            return files
            
        except zipfile.BadZipFile as e:
            raise NetworkError(f"Invalid ZIP file: {e}")
        except Exception as e:
            raise NetworkError(f"ZIP extraction failed: {e}")

    def get_repository_tree_api(self, owner: str, repo: str, branch: str = None) -> List[Dict[str, Any]]:
        """Get repository file tree using GitHub API (recursive)"""
        
        if not branch:
            branch = self.detect_default_branch(owner, repo)
        
        url = URLParser.build_api_url(owner, repo, f"git/trees/{branch}?recursive=1")
        
        try:
            response = self.session.get(url)
            self.rate_limit_manager.update_from_headers(response.headers)
            self.rate_limit_manager.consume_calls(1)
            
            tree_data = response.json()
            files = []
            
            for item in tree_data.get('tree', []):
                if item['type'] == 'blob':  # Only files, not directories
                    files.append({
                        'path': item['path'],
                        'size': item.get('size', 0),
                        'sha': item['sha'],
                        'url': item.get('url'),
                        'download_url': f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{quote(item['path'])}"
                    })
            
            self.logger.debug(f"Retrieved {len(files)} files via API")
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to get repository tree via API: {e}")
            raise

    def download_files_concurrently(self, files: List[Dict[str, Any]], max_workers: int = None) -> List[Dict[str, Any]]:
        """Download multiple files concurrently using API"""
        
        if not max_workers:
            max_workers = Config.get_max_concurrency(bool(self.token), self.rate_limit_manager.remaining)
        
        completed_files = []
        failed_files = []
        
        def download_single_file(file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Download a single file"""
            if not self.rate_limit_manager.check_rate_limit(1):
                return None  # Skip if rate limited
            
            try:
                response = self.session.get(file_info['download_url'], 
                                         timeout=Config.TIMEOUT_CONFIG['http_timeout'])
                self.rate_limit_manager.update_from_headers(response.headers)
                self.rate_limit_manager.consume_calls(1)
                
                content = response.content
                
                # Check file size
                if len(content) > Config.MAX_FILE_SIZE_BYTES:
                    self.logger.debug(f"Skipping large file: {file_info['path']} ({len(content)} bytes)")
                    return None
                
                # Decode content
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text_content = content.decode('latin-1')
                    except UnicodeDecodeError:
                        self.logger.debug(f"Skipping binary file: {file_info['path']}")
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
        
        # Execute downloads concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(download_single_file, file_info): file_info 
                            for file_info in files}
            
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        completed_files.append(result)
                    else:
                        failed_files.append(file_info)
                except Exception as e:
                    self.logger.debug(f"Future failed for {file_info['path']}: {e}")
                    failed_files.append(file_info)
        
        self.logger.debug(f"Downloaded {len(completed_files)} files, {len(failed_files)} failed")
        return completed_files

    def filter_and_prioritize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and prioritize files for download"""
        
        filtered_files = []
        
        for file_info in files:
            path = file_info['path']
            
            # Skip binary files
            if Config.is_binary_file(path):
                continue
            
            # Skip excluded directories
            if any(Config.is_excluded_directory(part) for part in path.split("/")):
                continue
            
            # Skip large files
            if file_info.get('size', 0) > Config.MAX_FILE_SIZE_BYTES:
                continue
            
            # Add priority scores
            file_info['priority'] = Config.get_file_priority(file_info['path'])
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

    def analyze_repository(self, owner: str, repo: str, method: str = "auto") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Main method to analyze repository using specified method"""
        
        # Get repository information
        repo_info = self.get_repository_info(owner, repo)
        
        # Check if repository is accessible
        if repo_info.get('private') and not self.token:
            raise AuthenticationError("Private repository requires GitHub token")
        
        if repo_info.get('disabled') or repo_info.get('archived'):
            self.logger.warning(f"Repository is {'disabled' if repo_info.get('disabled') else 'archived'}")
        
        # Determine method
        if method == "auto":
            # Estimate file count and suggest method
            estimated_files = min(repo_info.get('size', 0) // 10, 1000)  # Rough estimate
            method = self.rate_limit_manager.suggest_method(estimated_files)
            self.logger.debug(f"Auto-selected method: {method}")
        
        try:
            if method == "zip":
                files = self.download_repository_zip(owner, repo, repo_info['default_branch'])
            elif method == "api":
                # Get file tree first
                tree_files = self.get_repository_tree_api(owner, repo, repo_info['default_branch'])
                # Filter and prioritize files
                filtered_files = self.filter_and_prioritize_files(tree_files)
                # Download file contents
                files = self.download_files_concurrently(filtered_files)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Ensure files is always a list
            if not isinstance(files, list):
                self.logger.warning(f"Expected list from method {method}, got {type(files)}")
                files = []
            
            return files, repo_info
            
        except (NetworkError, RateLimitExceededError) as e:
            # Try fallback method
            if method == "api":
                self.logger.warning(f"API method failed: {e}. Trying ZIP method...")
                try:
                    files = self.download_repository_zip(owner, repo, repo_info['default_branch'])
                    return files if isinstance(files, list) else [], repo_info
                except Exception as fallback_e:
                    self.logger.error(f"ZIP fallback also failed: {fallback_e}")
                    return [], repo_info
            elif method == "zip":
                self.logger.warning(f"ZIP method failed: {e}. Trying API method...")
                try:
                    tree_files = self.get_repository_tree_api(owner, repo, repo_info['default_branch'])
                    filtered_files = self.filter_and_prioritize_files(tree_files)
                    files = self.download_files_concurrently(filtered_files)
                    return files if isinstance(files, list) else [], repo_info
                except Exception as fallback_e:
                    self.logger.error(f"API fallback also failed: {fallback_e}")
                    return [], repo_info
            else:
                raise

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information"""
        return {
            'limit': self.rate_limit_manager.limit,
            'remaining': self.rate_limit_manager.remaining,
            'reset_time': self.rate_limit_manager.reset_time,
            'reset_in_seconds': self.rate_limit_manager.wait_time_until_reset()
        }
