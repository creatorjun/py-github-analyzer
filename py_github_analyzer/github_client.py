"""
GitHub Client for py-github-analyzer v1.0.2
Enhanced synchronous GitHub API and ZIP downloading client
"""

import time
import zipfile
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import quote
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    REQUESTS_AVAILABLE = True
    
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
        """Suggest best method - ZIP-first strategy for all repositories"""
        return "zip"


class GitHubSession:
    """Enhanced requests session for GitHub API"""
    
    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required but not installed")
        
        self.session = requests.Session()
        self.token = token
        self.timeout = timeout

        if Retry is not None:
            try:
                retry_strategy = Retry(
                    total=3,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["HEAD", "GET", "OPTIONS"],
                    backoff_factor=1
                )
            except TypeError:
                try:
                    retry_strategy = Retry(
                        total=3,
                        status_forcelist=[429, 500, 502, 503, 504],
                        method_whitelist=["HEAD", "GET", "OPTIONS"],
                        backoff_factor=1
                    )
                except TypeError:
                    try:
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
                self.logger.debug(f"Failed to get repository info: {e}")
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
                    if self.token:
                        raise RepositoryNotFoundError(f"Repository {owner}/{repo} not found or you don't have access")
                    else:
                        raise PrivateRepositoryError(f"Repository {owner}/{repo} appears to be private or doesn't exist. Private repositories require a GitHub token.")
                elif any(keyword in error_message.lower() for keyword in ['private', 'authentication', '403']):
                    raise AuthenticationError("Repository not found, private, or requires authentication.\nPlease verify the repository URL and access permissions.")
                else:
                    raise NetworkError(f"Failed to get repository info: {e}")

    def detect_default_branch(self, owner: str, repo: str) -> str:
        """Detect the default branch of repository"""
        
        try:
            repo_info = self.get_repository_info(owner, repo, safe_mode=True)
            if repo_info.get('default_branch'):
                self.logger.debug(f"Default branch from repo info: {repo_info['default_branch']}")
                return repo_info['default_branch']
        except:
            pass
        
        branch_priority = ['main', 'master', 'develop', 'dev', 'trunk']
        
        for branch in branch_priority:
            try:
                url = URLParser.build_api_url(owner, repo, f"branches/{branch}")
                response = self.session.get(url)
                self.rate_limit_manager.update_from_headers(response.headers)
                self.rate_limit_manager.consume_calls(1)
                
                if response.ok:
                    self.logger.debug(f"Detected default branch via API: {branch}")
                    return branch
            except:
                continue
        
        for branch in ['main', 'master', 'develop']:
            for zip_url in self._get_zip_urls(owner, repo, branch):
                try:
                    response = self.session.session.head(zip_url, timeout=5)
                    if response.status_code == 200:
                        self.logger.debug(f"Detected branch via ZIP test: {branch}")
                        return branch
                except:
                    continue
        
        self.logger.warning("Could not detect default branch, using 'main'")
        return "main"

    def _get_zip_urls(self, owner: str, repo: str, branch: str) -> List[str]:
        """Get all possible ZIP URLs for a repository branch"""
        return [
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}",
            f"https://codeload.github.com/{owner}/{repo}/zip/{branch}",
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip",
            f"https://github.com/{owner}/{repo}/archive/{branch}.zip"
        ]

    def download_repository_zip(self, owner: str, repo: str, branch: str = None) -> List[Dict[str, Any]]:
        """Download repository as ZIP and extract file information"""
        
        if not branch:
            branch = self.detect_default_branch(owner, repo)
        
        possible_branches = [branch]
        if branch == 'main':
            possible_branches.extend(['master', 'develop', 'dev'])
        elif branch == 'master':
            possible_branches.extend(['main', 'develop', 'dev'])
        else:
            possible_branches.extend(['main', 'master', 'develop'])
        
        seen = set()
        unique_branches = []
        for b in possible_branches:
            if b not in seen:
                seen.add(b)
                unique_branches.append(b)
        
        possible_branches = unique_branches
        
        self.logger.debug(f"Trying branches in order: {possible_branches}")
        
        last_error = None
        
        for attempt_branch in possible_branches:
            possible_zip_urls = self._get_zip_urls(owner, repo, attempt_branch)
            
            self.logger.debug(f"Trying branch '{attempt_branch}' with {len(possible_zip_urls)} URL formats")
            
            for zip_url in possible_zip_urls:
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
                        timeout=Config.TIMEOUT_CONFIG.get('zip_timeout', 60),
                        stream=True,
                        allow_redirects=True,
                        headers=headers
                    )
                    
                    if response.status_code == 404:
                        self.logger.debug(f"ZIP URL not found: {zip_url}")
                        continue
                    elif response.status_code == 403:
                        raise PrivateRepositoryError(f"Repository {owner}/{repo} appears to be private")
                    elif response.status_code == 302:
                        self.logger.debug(f"ZIP URL redirect (normal): {zip_url}")
                    elif not response.ok:
                        self.logger.debug(f"ZIP URL failed with status {response.status_code}: {zip_url}")
                        continue
                    
                    if response.status_code in [200, 302]:
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', '')
                            if not any(ct in content_type.lower() for ct in ['zip', 'octet-stream', 'application']):
                                self.logger.debug(f"Wrong content-type {content_type}: {zip_url}")
                                continue
                            
                            content_length = response.headers.get('content-length')
                            if content_length:
                                size_mb = int(content_length) / 1024 / 1024
                                if size_mb > Config.MAX_TOTAL_SIZE_MB * 2:
                                    raise RepositoryTooLargeError(
                                        f"Repository ZIP too large: {size_mb:.1f}MB",
                                        size_mb,
                                        Config.MAX_TOTAL_SIZE_MB * 2
                                    )
                        
                        content = b''
                        downloaded = 0
                        chunk_size = 8192
                        
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                content += chunk
                                downloaded += len(chunk)
                                
                                content_length = response.headers.get('content-length')
                                if content_length and (downloaded % (chunk_size * 100) == 0):
                                    progress = (downloaded / int(content_length)) * 100
                                    self.logger.debug(f"Download progress: {progress:.1f}%")
                        
                        if len(content) < 100:
                            self.logger.debug(f"ZIP file too small ({len(content)} bytes): {zip_url}")
                            continue
                        
                        if not content.startswith(b'PK'):
                            self.logger.debug(f"Invalid ZIP signature: {zip_url}")
                            continue
                        
                        self.logger.info(f"ZIP download successful: {len(content)} bytes from {zip_url} (branch: {attempt_branch})")
                        return self._extract_zip_contents(content, f"{repo}-{attempt_branch}")
                    
                except requests.exceptions.RequestException as e:
                    last_error = e
                    self.logger.debug(f"ZIP download failed for {zip_url}: {e}")
                    continue
                except (NetworkError, RepositoryTooLargeError) as e:
                    last_error = e
                    self.logger.debug(f"ZIP processing failed for {zip_url}: {e}")
                    if isinstance(e, RepositoryTooLargeError):
                        raise
                    continue
                except Exception as e:
                    last_error = e
                    self.logger.debug(f"Unexpected error for {zip_url}: {e}")
                    continue
        
        self.logger.error(f"Failed to download ZIP for any branch {possible_branches}")
        if isinstance(last_error, (PrivateRepositoryError, AuthenticationError)):
            raise last_error
        else:
            raise NetworkError(f"Failed to download ZIP for any branch {possible_branches} using any URL format. Last error: {last_error}")

    def _extract_zip_contents(self, zip_content: bytes, expected_prefix: str) -> List[Dict[str, Any]]:
        """Extract file information from ZIP content"""
        files = []
        
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as zip_file:
                for zip_info in zip_file.infolist():
                    if zip_info.is_dir():
                        continue
                    
                    file_path = zip_info.filename
                    
                    if file_path.startswith(f"{expected_prefix}/"):
                        file_path = file_path[len(f"{expected_prefix}/"):]
                    elif "/" in file_path:
                        parts = file_path.split("/")
                        if len(parts) > 1:
                            file_path = "/".join(parts[1:])
                        else:
                            file_path = parts[0]
                    
                    if not file_path:
                        continue
                    
                    if any(Config.is_excluded_directory(part) for part in file_path.split("/")):
                        continue
                    
                    if Config.is_binary_file(file_path):
                        continue
                    
                    if zip_info.file_size > Config.MAX_FILE_SIZE_BYTES:
                        self.logger.debug(f"Skipping large file: {file_path} ({zip_info.file_size} bytes)")
                        continue
                    
                    try:
                        with zip_file.open(zip_info) as file:
                            content = file.read()
                        
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
            
            self.logger.info(f"Extracted {len(files)} files from ZIP")
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
                if item['type'] == 'blob':
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
                return None
            
            try:
                response = self.session.get(file_info['download_url'], 
                                         timeout=Config.TIMEOUT_CONFIG['http_timeout'])
                self.rate_limit_manager.update_from_headers(response.headers)
                self.rate_limit_manager.consume_calls(1)
                
                content = response.content
                
                if len(content) > Config.MAX_FILE_SIZE_BYTES:
                    self.logger.debug(f"Skipping large file: {file_info['path']} ({len(content)} bytes)")
                    return None
                
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
            
            if Config.is_binary_file(path):
                continue
            
            if any(Config.is_excluded_directory(part) for part in path.split("/")):
                continue
            
            if file_info.get('size', 0) > Config.MAX_FILE_SIZE_BYTES:
                continue
            
            file_info['priority'] = Config.get_file_priority(file_info['path'])
            filtered_files.append(file_info)
        
        filtered_files.sort(key=lambda x: x['priority'], reverse=True)
        
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
        
        repo_info = self.get_repository_info(owner, repo)
        
        if repo_info.get('private') and not self.token:
            raise AuthenticationError("Private repository requires GitHub token")
        
        if repo_info.get('disabled') or repo_info.get('archived'):
            self.logger.warning(f"Repository is {'disabled' if repo_info.get('disabled') else 'archived'}")
        
        if method == "auto":
            estimated_files = min(repo_info.get('size', 0) // 10, 1000)
            method = self.rate_limit_manager.suggest_method(estimated_files)
            self.logger.debug(f"Auto-selected method: {method}")
        
        try:
            if method == "zip":
                files = self.download_repository_zip(owner, repo, repo_info['default_branch'])
            elif method == "api":
                tree_files = self.get_repository_tree_api(owner, repo, repo_info['default_branch'])
                filtered_files = self.filter_and_prioritize_files(tree_files)
                files = self.download_files_concurrently(filtered_files)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            if not isinstance(files, list):
                self.logger.warning(f"Expected list from method {method}, got {type(files)}")
                files = []
            
            return files, repo_info
            
        except (NetworkError, RateLimitExceededError) as e:
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
