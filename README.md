# py-github-analyzer

High-performance async GitHub repository analyzer with AI-optimized code extraction and **smart .env file support**.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![PyPI Version](https://img.shields.io/pypi/v/py-github-analyzer.svg)](https://pypi.org/project/py-github-analyzer/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Async](https://img.shields.io/badge/async-first-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![.env Support](https://img.shields.io/badge/.env-supported-brightgreen.svg)](https://github.com/motdotla/dotenv)

## ✨ Features

- **🚀 Pure async architecture** - Built with modern async/await patterns for maximum performance
- **🔍 Smart repository analysis** - Automatic language detection and dependency mapping  
- **🔐 Private repository support** - Full GitHub token authentication with auto-detection
- **📁 Smart .env file support** - Automatically finds and loads tokens from .env files
- **📊 Multiple output formats** - JSON metadata and structured code extraction
- **🎯 Intelligent file filtering** - Skip binaries, focus on source code
- **🌍 Cross-platform compatibility** - Windows, macOS, and Linux support
- **💡 Smart error handling** - Graceful fallback and comprehensive error messages

## 📦 Installation

pip install py-github-analyzer


**All dependencies are automatically installed:**
- `httpx` - Modern async HTTP client
- `aiofiles` - Async file operations  
- `rich` - Beautiful terminal output
- `requests` - Fallback HTTP support
- **Built-in .env support** - No additional dependencies needed!

## 🔑 GitHub Token Setup (Recommended)

### 🎯 **Method 1: .env File (Recommended)**

**Create a `.env` file in your project directory:**

.env file
GITHUB_TOKEN=ghp_your_token_here

text

**Add .env to .gitignore for security:**

echo ".env" >> .gitignore


**That's it! The analyzer automatically finds and uses your token:**

No token parameter needed - automatically detected from .env!
py-github-analyzer https://github.com/user/repo


### 🔍 **Token Auto-Detection Priority**

The analyzer automatically searches for tokens in this order:

1. **`--github-token` parameter** (highest priority)
2. **`GITHUB_TOKEN` environment variable** 
3. **`GH_TOKEN` environment variable** (GitHub CLI compatible)
4. **`.env` file `GITHUB_TOKEN`** 🆕
5. **`.env` file `GH_TOKEN`** 🆕
6. **Anonymous access** (rate limited to 60 requests/hour)

### 📂 .env File Discovery

The analyzer automatically searches for `.env` files in:
- **Current working directory**
- **Parent directories** (up to 3 levels up)
- **Supports standard .env format:**
Comments are supported
GITHUB_TOKEN=ghp_your_token_here
GH_TOKEN="github_pat_alternative_token" # Quoted values work too


### 🛠️ **Other Token Setup Methods**

**Environment Variables:**
Linux/macOS
export GITHUB_TOKEN=ghp_your_token_here

Windows (Command Prompt)
set GITHUB_TOKEN=ghp_your_token_here

Windows (PowerShell)
$env:GITHUB_TOKEN="ghp_your_token_here"


**CLI Parameter:**
py-github-analyzer https://github.com/user/repo --github-token ghp_your_token_here


### 🔐 Creating a GitHub Token

1. Visit [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Select **`repo`** scope for private repository access
4. Copy the generated token (starts with `ghp_` or `github_pat_`)
5. Save in `.env` file or set as environment variable

## 🚀 Quick Start

### Command Line Interface

Basic usage (auto-detects token from .env file)
py-github-analyzer https://github.com/user/repo

Check .env file and token status
py-github-analyzer --check-env

With custom output directory
py-github-analyzer https://github.com/user/repo --output ./analysis

Private repository (token auto-detected from .env)
py-github-analyzer https://github.com/user/private-repo

JSON output only
py-github-analyzer https://github.com/user/repo --format json

Verbose output with detailed logging
py-github-analyzer https://github.com/user/repo --verbose

text

### Python API

import py_github_analyzer as pga

Simple analysis (auto-detects token from .env file)
result = pga.analyze_repository('https://github.com/user/repo')

Async analysis (recommended for better performance)
result = await pga.analyze_repository_async('https://github.com/user/repo')

With explicit GitHub token (overrides .env file)
result = pga.analyze_repository(
'https://github.com/user/repo',
github_token='ghp_your_token_here'
)

Advanced usage with custom options
result = await pga.analyze_repository_async(
'https://github.com/user/repo',
output_dir='./custom_results',
output_format='both', # json, bin, or both
method='auto', # auto, api, or zip
verbose=True
)

Class-based usage with automatic token detection
analyzer = pga.GitHubRepositoryAnalyzer() # Finds token automatically
result = await analyzer.analyze_repository('https://github.com/user/repo')

Check token sources and .env file status
token_info = pga.get_token_sources()
env_status = pga.check_env_file()


## 📁 Output Structure

The analyzer generates structured output files:

### Metadata Files
- `{owner}_{repo}_meta.json` - Complete repository metadata
- `{owner}_{repo}_compact_meta.json` - Compact metadata summary  
- `{owner}_{repo}_code.json` - Full source code extraction

### Example Metadata
{
"repo": "user/repository",
"desc": "A sample repository for demonstration",
"lang": ["Python", "JavaScript", "HTML"],
"size": "2.1MB",
"files": 45,
"main": ["main.py", "app.js", "index.html"],
"deps": ["requests", "numpy", "react", "express"]
}


## ⚙️ Configuration Options

### Command Line Arguments
py-github-analyzer <repository_url> [OPTIONS]

Options:
-o, --output DIR Output directory (default: ./results)
-f, --format FORMAT Output format: json, bin, both (default: both)
-t, --github-token TOKEN GitHub personal access token (overrides .env)
-m, --method METHOD Analysis method: auto, api, zip (default: auto)
-v, --verbose Enable verbose output
--dry-run Simulate analysis without processing
--no-fallback Disable fallback mode on errors
--check-env Check .env file and token status
--version Show version information


### Python API Options
await pga.analyze_repository_async(
repo_url='https://github.com/user/repo',
output_dir='./results', # Output directory
output_format='both', # json, bin, both
github_token=None, # Auto-detected from .env if None
method='auto', # auto, api, zip
verbose=False, # Enable detailed logging
dry_run=False, # Simulate without actual processing
fallback=True # Enable fallback on errors
)


## 🎯 Supported Languages & Features

### Programming Languages
- **Python** - `.py`, `requirements.txt`, `pyproject.toml`, `setup.py`
- **JavaScript/TypeScript** - `.js`, `.ts`, `.jsx`, `.tsx`, `package.json`
- **Java** - `.java`, `pom.xml`, `build.gradle`
- **C/C++** - `.c`, `.cpp`, `.h`, `.hpp`, `Makefile`, `CMakeLists.txt`
- **C#** - `.cs`, `.csproj`, `.sln`
- **Go** - `.go`, `go.mod`, `go.sum`
- **Rust** - `.rs`, `Cargo.toml`, `Cargo.lock`
- **PHP** - `.php`, `composer.json`
- **Ruby** - `.rb`, `Gemfile`
- **Swift** - `.swift`, `Package.swift`
- **Kotlin** - `.kt`, `.kts`
- **And many more...**

### Dependency Detection
- **Package managers** - npm, pip, Maven, Gradle, Cargo, Composer, Bundler
- **Configuration files** - Automatically parsed for dependencies
- **Version constraints** - Extracted when available

## 🚀 Performance & Architecture

### High-Performance Features
- **Async-first design** - Non-blocking I/O operations
- **Smart caching** - Efficient memory usage
- **Parallel processing** - Multiple files processed concurrently
- **ZIP-first strategy** - Faster than API for large repositories
- **Intelligent filtering** - Skip unnecessary files automatically

### Rate Limits & Token Benefits
- **Without token**: 60 requests/hour ⚠️
- **With token**: 5,000 requests/hour ✅
- **Smart detection**: Automatic rate limit management
- **Private repos**: Full access with proper token

## 🛡️ Error Handling

### Robust Error Management
- **Rate limit handling** - Automatic retry with exponential backoff
- **Network resilience** - Multiple fallback strategies
- **Partial analysis** - Continue processing on individual file errors
- **Graceful degradation** - Fallback mode for critical failures
- **Clear error messages** - Actionable error descriptions with token hints

### Exit Codes
- **0** - Success
- **1** - Error (validation, network, etc.)
- **2** - Success with warnings (fallback mode)
- **130** - Interrupted by user (Ctrl+C)

## 📋 Examples

### Basic Usage with .env File
1. Create .env file
echo "GITHUB_TOKEN=ghp_your_token_here" > .env
echo ".env" >> .gitignore

2. Analyze any repository - token auto-detected!
py-github-analyzer https://github.com/microsoft/vscode
py-github-analyzer https://github.com/facebook/react
py-github-analyzer https://github.com/your-org/private-repo


### Analyzing Popular Repositories
Large open source project
py-github-analyzer https://github.com/microsoft/vscode

Python project with dependencies
py-github-analyzer https://github.com/requests/requests

JavaScript/Node.js project
py-github-analyzer https://github.com/facebook/react

Check token status first
py-github-analyzer --check-env


### Batch Processing with .env Support
import py_github_analyzer as pga
import asyncio

async def analyze_multiple_repos():
# Token automatically loaded from .env file for all repos
repos = [
'https://github.com/user/repo1',
'https://github.com/user/repo2',
'https://github.com/user/private-repo' # Works with private repos too!
]


tasks = [pga.analyze_repository_async(repo) for repo in repos]
results = await asyncio.gather(*tasks)

for i, result in enumerate(results):
    print(f"Repository {i+1}: {result['metadata']['repo']}")
    print(f"  Language: {result['metadata']['lang']}")
    print(f"  Files: {len(result['files'])}")
Run batch analysis
asyncio.run(analyze_multiple_repos())


### Advanced Token Management
import py_github_analyzer as pga

Check what token sources are available
sources = pga.get_token_sources()
print("Token priority:", sources['priority_order'])

Check current .env file status
env_status = pga.check_env_file()
print(f"Found .env files: {env_status['env_files_found']}")

Get detailed token information
if pga.TokenUtils:
token = pga.TokenUtils.get_github_token()
info = pga.TokenUtils.get_token_info(token)
print(f"Token source: {info['source']}")
print(f"Token type: {info['type']}")


## 💡 Tips & Best Practices

### Security Best Practices
- ✅ **Use .env files** for local development
- ✅ **Add .env to .gitignore** to prevent accidental commits
- ✅ **Use environment variables** in production/CI/CD
- ✅ **Set minimal required permissions** when creating tokens
- ✅ **Rotate tokens regularly** for better security

### Performance Tips
- 🚀 **Always use tokens** for better rate limits (5000 vs 60 requests/hour)
- 🚀 **Use async API** for better performance in scripts
- 🚀 **Enable verbose mode** for debugging
- 🚀 **Use ZIP method** for large repositories (automatically chosen)

### Troubleshooting
Check if .env file is detected
py-github-analyzer --check-env

Test with verbose output
py-github-analyzer https://github.com/user/repo --verbose

Dry-run to test configuration
py-github-analyzer https://github.com/user/repo --dry-run


## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
git clone https://github.com/creatorjun/py-github-analyzer.git
cd py-github-analyzer

Create .env file for development
echo "GITHUB_TOKEN=your_dev_token" > .env
echo ".env" >> .gitignore

pip install -e .[dev]


## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📚 Changelog

### v1.0.0 (Latest)
- 🎉 **Initial stable release**
- 🚀 **Pure async architecture** for maximum performance
- 🔐 **Smart .env file support** with automatic token detection
- 📊 **Comprehensive repository analysis** with metadata generation
- 🌍 **Cross-platform support** (Windows, macOS, Linux)
- ⚡ **High-performance ZIP-first strategy**
- 🛡️ **Robust error handling** and fallback modes
- 💡 **Intelligent file filtering** and dependency detection
- 🔍 **Multi-source token detection** (env vars, .env files, parameters)

---

## 🔗 Links

- **PyPI**: https://pypi.org/project/py-github-analyzer/
- **GitHub**: https://github.com/creatorjun/py-github-analyzer
- **Documentation**: https://github.com/creatorjun/py-github-analyzer#readme
- **Issues**: https://github.com/creatorjun/py-github-analyzer/issues
- **Get GitHub Token**: https://github.com/settings/tokens

---

**Built with ❤️ by [Han Jun-hee](https://github.com/creatorjun)**

*Now with smart .env file support - because security shouldn't be complicated!*