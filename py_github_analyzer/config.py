"""
Configuration settings for py-github-analyzer v1.0.0
"""

import os
import tempfile
from typing import List, Dict, Any
from pathlib import Path


class Config:
    """Configuration constants and settings"""
    
    PACKAGE_NAME = "py-github-analyzer"
    VERSION = "1.0.0"
    AUTHOR = "Han Jun-hee"
    EMAIL = "createbrain2heart@gmail.com"
    
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
    GITHUB_CODELOAD_BASE = "https://codeload.github.com"
    
    DEFAULT_BRANCH_PRIORITY = ['main', 'master', 'develop', 'dev', 'trunk', 'release']
    
    RATE_LIMIT_BUFFER = 5
    MAX_CONCURRENT_DOWNLOADS = {
        'with_token': 10,
        'without_token': 3
    }
    
    MAX_FILE_SIZE_BYTES = 1024 * 1024
    MAX_TOTAL_SIZE_BYTES = 50 * 1024 * 1024
    MAX_TOTAL_SIZE_MB = 50
    
    TIMEOUT_CONFIG = {
        'http_timeout': 30,
        'zip_timeout': 60,
        'api_timeout': 30,
        'connection_timeout': 10
    }
    
    OUTPUT_FORMATS = ['json', 'bin', 'both']
    
    BINARY_FILE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.7z', '.rar', '.bz2',
        '.exe', '.dll', '.so', '.dylib', '.bin',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
        '.ttf', '.otf', '.woff', '.woff2',
        '.pyc', '.pyo', '.class', '.jar'
    }
    
    EXCLUDED_DIRECTORIES = {
        '.git', '.svn', '.hg',
        'node_modules', '__pycache__', '.pytest_cache',
        'dist', 'build', 'target', 'bin', 'obj',
        '.vscode', '.idea', '.vs',
        'tmp', 'temp', '.tmp',
        '.DS_Store', 'Thumbs.db',
        'venv', 'env', '.env', 'virtualenv'
    }
    
    HIGH_PRIORITY_FILES = {
        'package.json', 'requirements.txt', 'Gemfile', 'Cargo.toml',
        'setup.py', 'pyproject.toml', 'composer.json', 'pom.xml',
        'README.md', 'README.txt', 'README.rst', 'CHANGELOG.md',
        'LICENSE', 'LICENSE.txt', 'LICENSE.md',
        'main.py', 'app.py', 'index.js', 'main.js', 'server.js',
        'main.go', 'main.rs', 'Main.java'
    }
    
    HIGH_PRIORITY_EXTENSIONS = {
        '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h',
        '.cs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj'
    }
    
    MEDIUM_PRIORITY_EXTENSIONS = {
        '.html', '.css', '.scss', '.sass', '.less', '.vue', '.jsx', '.tsx',
        '.sql', '.sh', '.bash', '.ps1', '.yml', '.yaml', '.toml', '.ini'
    }
    
    DEFAULT_OUTPUT_DIR = "./analysis_results"
    DEFAULT_OUTPUT_FORMAT = "bin"
    
    LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    DEFAULT_LOG_LEVEL = 'INFO'
    
    @staticmethod
    def get_temp_dir() -> str:
        """Get temporary directory for downloads"""
        return os.path.join(tempfile.gettempdir(), Config.PACKAGE_NAME)
    
    @staticmethod
    def ensure_temp_dir() -> str:
        """Ensure temporary directory exists"""
        temp_dir = Config.get_temp_dir()
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
    @staticmethod
    def is_binary_file(file_path: str) -> bool:
        """Check if file is binary based on extension"""
        path = Path(file_path)
        return path.suffix.lower() in Config.BINARY_FILE_EXTENSIONS
    
    @staticmethod
    def is_excluded_directory(dir_name: str) -> bool:
        """Check if directory should be excluded"""
        return dir_name.lower() in Config.EXCLUDED_DIRECTORIES
    
    @staticmethod
    def get_file_priority(file_path: str) -> int:
        """Get priority score for file (higher = more important)"""
        path = Path(file_path)
        file_name = path.name.lower()
        extension = path.suffix.lower()
        
        if file_name in Config.HIGH_PRIORITY_FILES:
            return 100
        
        if extension in Config.HIGH_PRIORITY_EXTENSIONS:
            return 80
        
        if extension in Config.MEDIUM_PRIORITY_EXTENSIONS:
            return 60
        
        if 'config' in file_name or 'settings' in file_name:
            return 70
        
        if any(keyword in file_name for keyword in ['readme', 'doc', 'guide', 'tutorial']):
            return 65
        
        if any(keyword in file_name for keyword in ['test', 'spec']):
            return 40
        
        return 50
    
    @staticmethod
    def get_max_concurrency(has_token: bool, remaining_calls: int = 0) -> int:
        """Get maximum concurrent downloads based on token and rate limit"""
        base_concurrency = Config.MAX_CONCURRENT_DOWNLOADS['with_token' if has_token else 'without_token']
        
        if has_token and remaining_calls > 0:
            if remaining_calls < 100:
                base_concurrency = min(base_concurrency, 3)
            elif remaining_calls < 500:
                base_concurrency = min(base_concurrency, 5)
        
        return base_concurrency
    
    @staticmethod
    def get_github_zip_urls(owner: str, repo: str, branch: str) -> List[str]:
        """Get all possible GitHub ZIP download URLs for a repository"""
        return [
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}",
            f"https://codeload.github.com/{owner}/{repo}/zip/{branch}",
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip",
            f"https://github.com/{owner}/{repo}/archive/{branch}.zip"
        ]
    
    @staticmethod
    def validate_output_format(format_name: str) -> bool:
        """Validate output format name"""
        return format_name.lower() in Config.OUTPUT_FORMATS
    
    @staticmethod
    def get_user_agent() -> str:
        """Get User-Agent string for HTTP requests"""
        return f"{Config.PACKAGE_NAME}/{Config.VERSION} (Python)"
    
    FEATURES = {
        'async_support': True,
        'zip_first_strategy': True,
        'intelligent_fallback': True,
        'private_repo_detection': True,
        'smart_branch_detection': True,
        'concurrent_downloads': True,
        'compression_support': True,
        'metadata_generation': True
    }
    
    @staticmethod
    def is_feature_enabled(feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return Config.FEATURES.get(feature_name, False)


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEFAULT_LOG_LEVEL = 'DEBUG'
    MAX_CONCURRENT_DOWNLOADS = {'with_token': 5, 'without_token': 2}


class ProductionConfig(Config):
    """Production environment configuration"""
    DEFAULT_LOG_LEVEL = 'WARNING'
    TIMEOUT_CONFIG = {
        'http_timeout': 45,
        'zip_timeout': 90,
        'api_timeout': 45,
        'connection_timeout': 15
    }


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('PY_GITHUB_ANALYZER_ENV', 'production').lower()
    
    if env == 'development':
        return DevelopmentConfig()
    else:
        return ProductionConfig()


config = get_config()
