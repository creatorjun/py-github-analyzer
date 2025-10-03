"""
Configuration Module for py-github-analyzer v1.0.0
Centralized configuration management with enhanced settings and performance optimization
"""

from pathlib import Path


class Config:
    """Centralized configuration for py-github-analyzer v1.0.0"""
    
    # ===== PROJECT INFORMATION =====
    PACKAGE_NAME = "py-github-analyzer"
    VERSION = "1.0.0"
    AUTHOR = "Han Jun-hee"
    EMAIL = "createbrain2heart@gmail.com"
    
    # ===== FILE SIZE LIMITS =====
    MAX_FILES_COUNT = 1000
    MAX_TOTAL_SIZE_MB = 100
    MAX_FILE_SIZE_MB = 1
    MAX_TOTAL_SIZE_BYTES = MAX_TOTAL_SIZE_MB * 1024 * 1024
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # ===== GITHUB API CONFIGURATION =====
    GITHUB_API_BASE = "https://api.github.com"
    DEFAULT_BRANCH_PRIORITY = ["main", "master", "develop", "dev", "gh-pages"]
    
    # ===== RATE LIMIT MANAGEMENT =====
    RATE_LIMIT_BUFFER = 10
    MAX_CONCURRENT_DOWNLOADS = {
        "with_token": 50,      # Increased for v1.0.0 performance
        "without_token": 10    # Increased from 3 to 10
    }
    
    # ===== ASYNC-SPECIFIC SETTINGS =====
    ASYNC_CONFIG = {
        "max_semaphore_size": 100,     # Increased for better performance
        "connection_pool_size": 200,   # Increased pool size
        "httpx": {
            "keepalive_connections": 50,
            "keepalive_expiry": 30,
            "chunk_size": 8192,
            "progress_update_interval": 100
        }
    }
    
    # ===== COMPRESSION SETTINGS =====
    COMPRESSION_CONFIG = {
        "format": "gzip",
        "level": 6,
        "threshold_mb": 10
    }
    
    # ===== RETRY CONFIGURATION =====
    RETRY_CONFIG = {
        "max_retries": 3,
        "base_delay": 1,
        "max_delay": 32,
        "backoff_factor": 2,
        "jitter": True
    }
    
    # ===== NETWORK TIMEOUTS =====
    TIMEOUT_CONFIG = {
        "http_timeout": 30,      # HTTP requests
        "zip_timeout": 180,      # ZIP downloads (increased from 120)
        "api_timeout": 20,       # API calls (increased from 15)
        "connect_timeout": 15,   # Connection timeout (increased)
        "read_timeout": 45,      # Read timeout (increased)
        "write_timeout": 30      # Write timeout
    }
    
    # ===== FILE PRIORITY PATTERNS (1000 point system) =====
    FILE_PRIORITY_PATTERNS = {
        # Entry points (1000 points)
        "main.py": 1000, "app.py": 1000, "index.js": 1000, "index.ts": 1000,
        "server.js": 1000, "run.py": 1000, "__main__.py": 1000, "cli.py": 950,
        "manage.py": 1000, "wsgi.py": 950, "asgi.py": 950,
        
        # Configuration files (900 points)  
        "package.json": 900, "pyproject.toml": 900, "setup.py": 900, 
        "requirements.txt": 900, "dockerfile": 900, "docker-compose.yml": 900,
        "makefile": 900, "cmake.txt": 900, "cargo.toml": 900, "go.mod": 900,
        
        # Documentation (800 points)
        "readme.md": 800, "readme.txt": 800, "license": 800, "license.txt": 800,
        "license.md": 800, "changelog.md": 800, "contributing.md": 800,
        "docs.md": 750, "api.md": 750,
        
        # Source directories (700-600 points)
        "/src/": 700, "/lib/": 600, "/app/": 650, "/core/": 620,
        "/utils/": 580, "/components/": 580, "/modules/": 580, "/api/": 620,
        
        # Test files (400 points)
        "/test/": 400, "/tests/": 400, "/spec/": 400, "test_": 400, "_test.": 400,
        
        # Build and deployment (300-200 points)
        "/.github/": 300, "/scripts/": 300, "/build/": 200, "/dist/": 200,
        
        # Low priority (100-50 points)
        "/node_modules/": 50, "/.git/": 50, "/__pycache__/": 50, 
        "/.pytest_cache/": 50, "/venv/": 50, "/.venv/": 50
    }
    
    # ===== LANGUAGE-SPECIFIC PRIORITY PATTERNS =====
    LANGUAGE_PRIORITY_PATTERNS = {
        "python": {
            "entry_points": ["main.py", "__main__.py", "app.py", "run.py", "manage.py"],
            "config_files": ["setup.py", "pyproject.toml", "requirements.txt", "setup.cfg", "tox.ini"],
            "important_dirs": ["src", "app", "lib", "core"],
            "framework_files": {
                "django": ["manage.py", "settings.py", "urls.py", "wsgi.py", "asgi.py"],
                "flask": ["app.py", "run.py", "config.py", "__init__.py"],
                "fastapi": ["main.py", "app.py", "api.py"],
                "pytest": ["conftest.py", "test_*.py", "*_test.py"]
            }
        },
        "javascript": {
            "entry_points": ["index.js", "main.js", "app.js", "server.js", "index.ts", "main.ts"],
            "config_files": ["package.json", "webpack.config.js", "vite.config.js", "tsconfig.json", ".eslintrc.js"],
            "important_dirs": ["src", "lib", "app", "components"],
            "framework_files": {
                "react": ["App.jsx", "App.tsx", "index.jsx", "index.tsx", "src/App.js"],
                "vue": ["main.js", "App.vue", "vue.config.js", "nuxt.config.js"],
                "nextjs": ["next.config.js", "pages/_app.js", "pages/index.js"],
                "express": ["server.js", "app.js", "index.js"],
                "nestjs": ["main.ts", "app.module.ts", "app.controller.ts"]
            }
        },
        "typescript": {
            "entry_points": ["index.ts", "main.ts", "app.ts", "server.ts"],
            "config_files": ["tsconfig.json", "package.json", "webpack.config.ts"],
            "important_dirs": ["src", "lib", "types"],
            "framework_files": {
                "angular": ["main.ts", "app.module.ts", "app.component.ts"],
                "nestjs": ["main.ts", "app.module.ts", "app.controller.ts"]
            }
        },
        "java": {
            "entry_points": ["Main.java", "Application.java", "App.java"],
            "config_files": ["pom.xml", "build.gradle", "application.properties", "application.yml"],
            "important_dirs": ["src/main", "src/test"],
            "framework_files": {
                "spring": ["Application.java", "*Controller.java", "*Service.java", "*Repository.java"],
                "maven": ["pom.xml"],
                "gradle": ["build.gradle", "settings.gradle"]
            }
        },
        "go": {
            "entry_points": ["main.go", "cmd/main.go"],
            "config_files": ["go.mod", "go.sum", "Makefile", "Dockerfile"],
            "important_dirs": ["cmd", "internal", "pkg", "api"],
            "framework_files": {
                "gin": ["main.go", "*router.go"],
                "echo": ["main.go", "*handler.go"]
            }
        },
        "rust": {
            "entry_points": ["main.rs", "lib.rs"],
            "config_files": ["Cargo.toml", "Cargo.lock"],
            "important_dirs": ["src", "tests"],
            "framework_files": {
                "actix": ["main.rs", "*handlers.rs"],
                "rocket": ["main.rs", "*routes.rs"]
            }
        }
    }
    
    # ===== FILE EXTENSIONS TO LANGUAGE MAPPING =====
    EXTENSION_TO_LANGUAGE = {
        # Programming languages
        ".py": "python", ".js": "javascript", ".jsx": "javascript", 
        ".ts": "typescript", ".tsx": "typescript", ".java": "java",
        ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
        ".h": "c", ".hpp": "cpp", ".php": "php", ".rb": "ruby", ".swift": "swift",
        ".kt": "kotlin", ".scala": "scala", ".cs": "csharp", ".fs": "fsharp",
        ".clj": "clojure", ".hs": "haskell", ".ml": "ocaml", ".r": "r", ".m": "matlab",
        
        # Scripting and shell
        ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "shell", 
        ".ps1": "powershell", ".sql": "sql",
        
        # Web technologies
        ".html": "html", ".css": "css", ".scss": "scss", ".sass": "sass", 
        ".less": "less", ".xml": "xml",
        
        # Data formats
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".ini": "ini", ".cfg": "ini", ".conf": "conf",
        
        # Documentation
        ".md": "markdown", ".txt": "text"
    }
    
    # ===== BINARY FILE EXTENSIONS TO EXCLUDE =====
    BINARY_EXTENSIONS = {
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff", ".tga",
        # Audio
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
        # Video  
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        # Archives
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tar.gz", ".tar.bz2",
        # Executables
        ".exe", ".dll", ".so", ".dylib", ".app", ".deb", ".rpm", ".msi", ".dmg",
        # Documents
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        # Fonts
        ".ttf", ".otf", ".woff", ".woff2", ".eot",
        # Databases
        ".db", ".sqlite", ".sqlite3", ".mdb",
        # Other binaries
        ".bin", ".dat", ".dump", ".img", ".iso", ".lock"
    }
    
    # ===== DIRECTORIES TO EXCLUDE =====
    EXCLUDED_DIRECTORIES = {
        # Version control
        ".git", ".svn", ".hg", ".bzr",
        # Dependencies
        "node_modules", "__pycache__", ".pytest_cache", "venv", ".venv", "env", ".env",
        # Build outputs
        "build", "dist", "target", "out", "bin", "obj",
        # IDE/Editor
        ".idea", ".vscode", ".vs",
        # Logs and temporary
        "logs", "log", "tmp", "temp",
        # Testing and coverage
        ".tox", ".coverage", ".nyc_output",
        # Language specific
        "vendor", "Pods",  # Dependency managers
        ".next", ".nuxt",  # Framework specific
        ".cache"          # Cache directories
    }
    
    # ===== PERFORMANCE LIMITS =====
    PERFORMANCE_LIMITS = {
        "memory_limit_mb": 1000,      # Increased from 500
        "file_cache_size": 200,       # Increased from 100  
        "max_concurrent_files": 100   # Increased from 50
    }
    
    # ===== OUTPUT FORMAT CONFIGURATIONS =====
    OUTPUT_FORMATS = ["bin", "json", "both"]
    
    # ===== HELPER METHODS =====
    @classmethod
    def get_file_priority(cls, file_path: str) -> int:
        """Calculate file priority based on patterns"""
        file_path_lower = file_path.lower()
        
        # Check exact filename matches first
        filename = Path(file_path_lower).name
        if filename in cls.FILE_PRIORITY_PATTERNS:
            return cls.FILE_PRIORITY_PATTERNS[filename]
        
        # Check directory patterns
        for pattern, priority in cls.FILE_PRIORITY_PATTERNS.items():
            if pattern.endswith("/") and pattern[:-1] in file_path_lower:
                return priority
        
        # Check filename patterns (test_, _test., etc.)
        for pattern, priority in cls.FILE_PRIORITY_PATTERNS.items():
            if not pattern.endswith("/") and pattern in filename:
                return priority
                
        return 100  # Default priority
    
    @classmethod
    def is_binary_file(cls, file_path: str) -> bool:
        """Check if file is binary based on extension"""
        extension = Path(file_path).suffix.lower()
        return extension in cls.BINARY_EXTENSIONS
    
    @classmethod
    def is_excluded_directory(cls, dir_path: str) -> bool:
        """Check if directory should be excluded"""
        dir_name = Path(dir_path).name.lower()
        return dir_name in cls.EXCLUDED_DIRECTORIES
    
    @classmethod
    def get_language_from_extension(cls, file_path: str) -> str:
        """Get programming language from file extension"""
        extension = Path(file_path).suffix.lower()
        return cls.EXTENSION_TO_LANGUAGE.get(extension, "unknown")
    
    @classmethod
    def get_max_concurrency(cls, has_token: bool, rate_remaining: int = None) -> int:
        """Calculate optimal concurrency based on token and rate limits"""
        base_concurrency = cls.MAX_CONCURRENT_DOWNLOADS["with_token"] if has_token else cls.MAX_CONCURRENT_DOWNLOADS["without_token"]
        
        if rate_remaining is not None and has_token:
            # Conservative approach: use only 1/5 of remaining calls
            safe_concurrency = max(1, rate_remaining // 20)
            return min(base_concurrency, safe_concurrency)
        
        return base_concurrency
    
    @classmethod
    def get_async_semaphore_size(cls, has_token: bool, rate_remaining: int = None) -> int:
        """Get optimal semaphore size for async operations"""
        base_size = cls.ASYNC_CONFIG["max_semaphore_size"] if has_token else 10
        
        if rate_remaining is not None:
            # Conservative approach: use only 1/10 of remaining calls for semaphore
            safe_size = max(5, min(rate_remaining // 10, base_size))
            return safe_size
        
        return min(base_size, 30) if has_token else min(base_size, 10)
    
    @classmethod
    def get_httpx_timeout(cls) -> dict:
        """Get httpx timeout configuration"""
        return {
            "connect": cls.TIMEOUT_CONFIG["connect_timeout"],
            "read": cls.TIMEOUT_CONFIG["read_timeout"], 
            "write": cls.TIMEOUT_CONFIG["write_timeout"],
            "pool": cls.TIMEOUT_CONFIG["api_timeout"]
        }
    
    @classmethod
    def get_version_info(cls) -> dict:
        """Get complete version and package information"""
        return {
            "name": cls.PACKAGE_NAME,
            "version": cls.VERSION,
            "author": cls.AUTHOR,
            "email": cls.EMAIL,
            "description": "AI-optimized GitHub repository analyzer with enhanced private repository support",
            "features": [
                "ZIP-first access strategy for optimal performance",
                "Enhanced private repository detection and guidance",
                "High-performance async processing with parallel downloads",
                "AI-optimized output format for machine learning applications",
                "Smart language detection and file prioritization",
                "Comprehensive error handling with actionable solutions",
                "Multiple download methods (ZIP, API, auto-selection)",
                "Advanced rate limit management and token optimization",
                "Intelligent branch detection with fallback mechanisms",
                "Multiple output formats (JSON, compressed binary)"
            ]
        }
