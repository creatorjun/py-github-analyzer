"""
Configuration module for py-github-analyzer v1.0.0
Central configuration and constants
"""

class Config:
    """Central configuration class"""
    
    VERSION = "1.0.0"
    PACKAGE_NAME = "py-github-analyzer"
    
    # GitHub API configuration
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
    GITHUB_ARCHIVE_BASE = "https://github.com"
    
    # Branch priority for repository analysis
    DEFAULT_BRANCH_PRIORITY = [
        'main',
        'master', 
        'develop',
        'dev',
        'development',
        'trunk'
    ]
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 60  # requests per hour without token
    AUTHENTICATED_RATE_LIMIT = 5000  # requests per hour with token
    RATE_LIMIT_BUFFER = 5  # safety buffer for rate limits
    
    # Timeouts (in seconds)
    REQUEST_TIMEOUT = 30
    DOWNLOAD_TIMEOUT = 300  # 5 minutes for large repositories
    
    # File processing
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
    MAX_REPOSITORY_SIZE = 500 * 1024 * 1024  # 500MB total
    MAX_TOTAL_SIZE_MB = 500  # Maximum total repository size in MB
    MAX_INDIVIDUAL_FILE_SIZE_MB = 10  # Maximum individual file size in MB
    MAX_FILES_COUNT = 10000  # maximum files to process
    
    # Output formats
    OUTPUT_FORMATS = ["json", "bin", "both"]
    DEFAULT_OUTPUT_FORMAT = "both"
    
    # Supported file extensions for analysis
    SUPPORTED_EXTENSIONS = {
        'python': ['.py', '.pyx', '.pyi'],
        'javascript': ['.js', '.jsx', '.mjs', '.ts', '.tsx'],
        'java': ['.java', '.class'],
        'cpp': ['.cpp', '.cxx', '.cc', '.c', '.hpp', '.h'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'rust': ['.rs'],
        'php': ['.php', '.phtml'],
        'ruby': ['.rb'],
        'swift': ['.swift'],
        'kotlin': ['.kt', '.kts'],
        'scala': ['.scala'],
        'shell': ['.sh', '.bash', '.zsh'],
        'sql': ['.sql'],
        'html': ['.html', '.htm'],
        'css': ['.css', '.scss', '.sass', '.less'],
        'markdown': ['.md', '.markdown'],
        'yaml': ['.yml', '.yaml'],
        'json': ['.json'],
        'xml': ['.xml'],
        'dockerfile': ['Dockerfile', '.dockerfile'],
        'config': ['.ini', '.cfg', '.conf', '.toml']
    }

    # Binary extensions to skip
    BINARY_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.a', '.lib', '.o', '.obj',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.woff', '.woff2', '.ttf', '.eot', '.otf'
    }

    # Files to always skip
    SKIP_FILES = {
        '.gitignore', '.gitattributes', '.gitmodules',
        'LICENSE', 'LICENCE', 'COPYING',
        'CHANGELOG', 'CHANGELOG.md', 'CHANGES',
        '.DS_Store', 'Thumbs.db',
        '.eslintrc', '.prettierrc', '.editorconfig'
    }

    # Directories to skip
    SKIP_DIRECTORIES = {
        '.git', '.svn', '.hg', '.bzr',
        'node_modules', '__pycache__', '.pytest_cache',
        'venv', 'env', '.env', '.venv',
        'build', 'dist', 'target', 'out',
        '.idea', '.vscode', '.vs',
        'coverage', '.coverage', '.nyc_output',
        'logs', 'tmp', 'temp', '.tmp'
    }

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'python': {'extensions': ['.py'], 'files': ['setup.py', 'requirements.txt']},
        'javascript': {'extensions': ['.js', '.jsx'], 'files': ['package.json', 'yarn.lock']},
        'typescript': {'extensions': ['.ts', '.tsx'], 'files': ['tsconfig.json']},
        'java': {'extensions': ['.java'], 'files': ['pom.xml', 'build.gradle']},
        'cpp': {'extensions': ['.cpp', '.c', '.hpp', '.h'], 'files': ['Makefile', 'CMakeLists.txt']},
        'csharp': {'extensions': ['.cs'], 'files': ['.csproj', '.sln']},
        'go': {'extensions': ['.go'], 'files': ['go.mod', 'go.sum']},
        'rust': {'extensions': ['.rs'], 'files': ['Cargo.toml', 'Cargo.lock']},
        'php': {'extensions': ['.php'], 'files': ['composer.json']},
        'ruby': {'extensions': ['.rb'], 'files': ['Gemfile', 'Rakefile']},
    }

    # Dependency detection patterns
    DEPENDENCY_FILES = {
        'python': ['requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py'],
        'javascript': ['package.json', 'yarn.lock', 'package-lock.json'],
        'java': ['pom.xml', 'build.gradle', 'gradle.properties'],
        'csharp': ['.csproj', 'packages.config', '.nuspec'],
        'go': ['go.mod', 'go.sum', 'Gopkg.toml'],
        'rust': ['Cargo.toml', 'Cargo.lock'],
        'php': ['composer.json', 'composer.lock'],
        'ruby': ['Gemfile', 'Gemfile.lock', '.gemspec']
    }

    # Analysis methods
    ANALYSIS_METHODS = ["auto", "api", "zip"]
    DEFAULT_ANALYSIS_METHOD = "auto"
    
    # Compression settings
    COMPRESSION_LEVEL = 6  # balance between speed and size
    CHUNK_SIZE = 8192  # 8KB chunks for streaming
    
    @classmethod
    def get_file_category(cls, filename: str) -> str:
        """Get file category based on extension"""
        if not filename:
            return 'unknown'
        
        # Handle special files
        if filename in cls.SKIP_FILES:
            return 'skip'
        
        # Get extension
        if '.' in filename:
            ext = '.' + filename.split('.')[-1].lower()
        else:
            ext = filename.lower()
        
        # Check binary extensions
        if ext in cls.BINARY_EXTENSIONS:
            return 'binary'
        
        # Check supported extensions
        for category, extensions in cls.SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return category
        
        return 'text'
    
    @classmethod
    def should_skip_directory(cls, dirname: str) -> bool:
        """Check if directory should be skipped"""
        return dirname.lower() in cls.SKIP_DIRECTORIES
    
    @classmethod
    def should_skip_file(cls, filename: str) -> bool:
        """Check if file should be skipped"""
        return filename in cls.SKIP_FILES or cls.get_file_category(filename) == 'binary'
