import re
import os
import gzip
import bz2
import lzma
import random
import mimetypes
from pathlib import Path
from typing import Dict, Tuple, Union, Callable
import tempfile
import shutil
from contextlib import contextmanager
from functools import wraps, lru_cache

from .config import Config
from .exceptions import (
    ValidationError,
    CompressionError,
)


class URLParser:
    """GitHub URL parsing and validation utilities"""
    
    GITHUB_URL_PATTERN = re.compile(
        r'^(?:https?://)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)(?:\.git)?/?(?P<path>.*)?$',
        re.IGNORECASE
    )

    @classmethod
    def parse_github_url(cls, url: str) -> Dict[str, str]:
        """
        Parse GitHub URL and extract owner, repo, and optional path
        Enhanced version with better validation and fallback handling
        """
        if not url:
            raise ValidationError("Empty URL provided")
        
        # Clean up URL
        url = url.strip().rstrip('/')
        
        # Enhanced URL preprocessing
        if not url.startswith(('http', 'https')):
            if url.startswith('github.com/'):
                url = f"https://{url}"
            elif '/' in url and len(url.split('/')) >= 2 and not url.startswith('github.com'):
                # Handle cases like "user/repo" or "user/repo.git"
                url = f"https://github.com/{url}"
            else:
                # Last resort - assume it's a github URL
                url = f"https://github.com/{url}"
        
        # Remove .git extension if present
        if url.endswith('.git'):
            url = url[:-4]
        
        # Enhanced regex pattern for better matching
        github_url_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?github\.com/'
            r'(?P<owner>[a-zA-Z0-9]([a-zA-Z0-9\-_]*[a-zA-Z0-9])?)'
            r'/(?P<repo>[a-zA-Z0-9\._\-]+)'
            r'(?:\.git)?'
            r'(?:/(?P<path>.*))?',
            re.IGNORECASE
        )
        
        match = github_url_pattern.match(url)
        if not match:
            raise ValidationError(f"Invalid GitHub URL format: {url}")
        
        result = {
            'owner': match.group('owner'),
            'repo': match.group('repo'), 
            'path': match.group('path') or '',
            'full_name': f"{match.group('owner')}/{match.group('repo')}"
        }
        
        # Enhanced validation
        if not cls._is_valid_github_username(result['owner']):
            raise ValidationError(f"Invalid GitHub username: {result['owner']}")
        
        if not cls._is_valid_github_repository_name(result['repo']):
            raise ValidationError(f"Invalid GitHub repository name: {result['repo']}")
        
        return result

    @staticmethod
    def _is_valid_github_username(name: str) -> bool:
        """Validate GitHub username with stricter rules"""
        if not name or len(name) > 39:
            return False
        
        # GitHub username rules: alphanumeric and hyphens only, no consecutive hyphens
        if name.startswith('-') or name.endswith('-'):
            return False
        
        # No consecutive hyphens
        if '--' in name:
            return False
        
        # Only alphanumeric and single hyphens
        username_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$')
        return bool(username_pattern.match(name))

    @staticmethod  
    def _is_valid_github_repository_name(name: str) -> bool:
        """Validate GitHub repository name with flexible rules"""
        if not name or len(name) > 100:
            return False
        
        # Cannot start with . or -
        if name.startswith('.') or name.startswith('-'):
            return False
        
        # Allow "invalid-url" as it contains valid characters
        # Allow alphanumeric, hyphens, underscores, and periods
        repo_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-\._]*[a-zA-Z0-9])?$')
        return bool(repo_pattern.match(name))

    @staticmethod
    def is_valid_github_name(name: str) -> bool:
        """Legacy method - use specific username or repository validation instead"""
        # Default to repository name validation for backward compatibility
        return URLParser.is_valid_github_repository_name(name)

    @staticmethod
    def build_api_url(owner: str, repo: str, endpoint: str = "contents") -> str:
        """Build GitHub API URL"""
        base_url = Config.GITHUB_API_BASE
        return f"{base_url}/repos/{owner}/{repo}/{endpoint}"

    @staticmethod
    def build_zip_url(owner: str, repo: str, branch: str = "main") -> str:
        """Build GitHub ZIP download URL"""
        return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"


class FileUtils:
    """File and directory utilities"""

    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Ensure directory exists and return Path object"""
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj

    @staticmethod
    def safe_filename(filename: str) -> str:
        """Create safe filename by removing/replacing invalid characters"""
        # Replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[\x00-\x1f]', '', filename)  # Remove control characters
        
        # Truncate if too long
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:195] + ext
        
        return filename.strip('. ')  # Remove leading/trailing dots and spaces

    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """Get file size in bytes"""
        try:
            return Path(file_path).stat().st_size
        except (OSError, FileNotFoundError):
            return 0

    @staticmethod
    def calculate_directory_size(directory: Union[str, Path]) -> Tuple[int, int]:
        """Calculate total size and file count of directory"""
        total_size = 0
        file_count = 0
        
        try:
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file():
                    total_size += FileUtils.get_file_size(file_path)
                    file_count += 1
        except (OSError, PermissionError):
            pass
        
        return total_size, file_count

    @staticmethod
    def is_text_file(file_path: Union[str, Path]) -> bool:
        """Check if file is likely a text file"""
        path_obj = Path(file_path)
        
        # Check by extension first
        if Config.is_binary_file(str(path_obj)):
            return False
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(path_obj))
        if mime_type and mime_type.startswith('text'):
            return True
        
        # Check file content (first 1024 bytes)
        try:
            with open(path_obj, 'rb') as f:
                chunk = f.read(1024)
                if not chunk:
                    return True  # Empty file
                
                # Look for null bytes (strong indicator of binary)
                if b'\x00' in chunk:
                    return False
                
                # Check for high percentage of printable characters
                printable_chars = sum(1 for byte in chunk if 32 <= byte <= 126 or byte in [9, 10, 13])
                return (printable_chars / len(chunk)) > 0.7
        except (OSError, UnicodeDecodeError):
            return False

    @staticmethod
    def read_file_safe(file_path: Union[str, Path], encoding: str = 'utf-8', fallback_encoding: str = 'latin-1') -> str:
        """Safely read text file with encoding fallback"""
        path_obj = Path(file_path)
        
        for enc in [encoding, fallback_encoding, 'utf-8', 'ascii']:
            try:
                with open(path_obj, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue
        
        # Last resort: read as binary and decode with errors='replace'
        try:
            with open(path_obj, 'rb') as f:
                return f.read().decode('utf-8', errors='replace')
        except OSError as e:
            raise ValidationError(f"Cannot read file {file_path}: {e}")

    @contextmanager
    def temp_directory():
        """Context manager for temporary directory"""
        temp_dir = tempfile.mkdtemp(prefix='github_analyzer_')
        try:
            yield Path(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class CompressionUtils:
    """Compression and decompression utilities"""

    @staticmethod
    def compress_data(data: Union[str, bytes], format_type: str = "gzip", level: int = 6) -> bytes:
        """Compress data using specified format"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        try:
            if format_type.lower() == "gzip":
                return gzip.compress(data, compresslevel=level)
            elif format_type.lower() == "bz2":
                return bz2.compress(data, compresslevel=level)
            elif format_type.lower() == "lzma":
                return lzma.compress(data, preset=level)
            else:
                raise CompressionError(f"Unsupported compression format: {format_type}")
        except Exception as e:
            raise CompressionError(f"Compression failed: {e}")

    @staticmethod
    def decompress_data(data: bytes, format_type: str = "gzip") -> str:
        """Decompress data using specified format and return as string"""
        try:
            decompressed_bytes = None
            
            if format_type.lower() == "gzip":
                decompressed_bytes = gzip.decompress(data)
            elif format_type.lower() == "bz2":
                decompressed_bytes = bz2.decompress(data)
            elif format_type.lower() == "lzma":
                decompressed_bytes = lzma.decompress(data)
            else:
                raise CompressionError(f"Unsupported decompression format: {format_type}")
            
            # Convert bytes to string
            return decompressed_bytes.decode('utf-8')
            
        except UnicodeDecodeError as e:
            raise CompressionError(f"Failed to decode decompressed data as UTF-8: {e}")
        except Exception as e:
            raise CompressionError(f"Decompression failed: {e}")

    @staticmethod
    def decompress_to_bytes(data: bytes, format_type: str = "gzip") -> bytes:
        """Decompress data using specified format and return as bytes"""
        try:
            if format_type.lower() == "gzip":
                return gzip.decompress(data)
            elif format_type.lower() == "bz2":
                return bz2.decompress(data)
            elif format_type.lower() == "lzma":
                return lzma.decompress(data)
            else:
                raise CompressionError(f"Unsupported decompression format: {format_type}")
        except Exception as e:
            raise CompressionError(f"Decompression failed: {e}")

    @staticmethod
    def should_compress(data_size_mb: float) -> bool:
        """Determine if data should be compressed based on size"""
        return data_size_mb >= Config.COMPRESSION_CONFIG.get("threshold_mb", 1.0)

    @staticmethod
    def estimate_compression_ratio(data: Union[str, bytes], format_type: str = "gzip") -> float:
        """Estimate compression ratio without full compression"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Sample-based estimation for large data
        sample_size = min(len(data), 10240)  # 10KB sample
        sample_data = data[:sample_size]
        
        try:
            compressed_sample = CompressionUtils.compress_data(sample_data, format_type)
            ratio = len(compressed_sample) / len(sample_data)
            return ratio
        except CompressionError:
            return 1.0  # No compression benefit

class RetryUtils:
    """Retry logic utilities"""
    
    @staticmethod
    def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 32.0,
                           backoff_factor: float = 2.0, jitter: bool = True) -> float:
        """Calculate delay for exponential backoff"""
        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
        
        if jitter:
            # Add random jitter (±10%)
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


class TextUtils:
    """Text processing utilities"""
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to maximum length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix


class ValidationUtils:
    """Data validation utilities"""
    
    @staticmethod
    def validate_output_format(format_str: str) -> bool:
        """Validate output format string"""
        return format_str.lower() in Config.OUTPUT_FORMATS

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitize file path for safe processing"""
        # Remove any path traversal attempts
        path = path.replace('..', '').replace('//', '/')
        
        # Remove leading slashes
        path = path.lstrip('/')
        
        # Normalize path separators
        path = path.replace('\\', '/')
        
        return path
