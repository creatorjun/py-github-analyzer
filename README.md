# py-github-analyzer

High-performance async GitHub repository analyzer with AI-optimized code extraction and automatic token detection.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![PyPI Version](https://img.shields.io/pypi/v/py-github-analyzer.svg)](https://pypi.org/project/py-github-analyzer/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Async](https://img.shields.io/badge/async-first-green.svg)](https://docs.python.org/3/library/asyncio.html)

## ✨ Features

- **🚀 Pure async architecture** - Built with modern async/await patterns for maximum performance
- **🔍 Smart repository analysis** - Automatic language detection and dependency mapping  
- **🔐 Private repository support** - Full GitHub token authentication with auto-detection
- **📊 Multiple output formats** - JSON metadata and structured code extraction
- **🎯 Intelligent file filtering** - Skip binaries, focus on source code
- **🌍 Cross-platform compatibility** - Windows, macOS, and Linux support
- **⚡ Environment variable support** - Automatic token detection from `GITHUB_TOKEN` or `GH_TOKEN`
- **💡 Smart error handling** - Graceful fallback and comprehensive error messages

## 📦 Installation

pip install py-github-analyzer


**All dependencies are automatically installed:**
- `httpx` - Modern async HTTP client
- `aiofiles` - Async file operations  
- `rich` - Beautiful terminal output
- `requests` - Fallback HTTP support

## 🚀 Quick Start

### Command Line Interface

Basic usage (auto-detects GITHUB_TOKEN environment variable)
py-github-analyzer https://github.com/user/repo

With custom output directory
py-github-analyzer https://github.com/user/repo --output ./analysis

Private repository with token parameter
py-github-analyzer https://github.com/user/private-repo --github-token ghp_your_token_here

JSON output only
py-github-analyzer https://github.com/user/repo --format json

Verbose output with detailed logging
py-github-analyzer https://github.com/user/repo --verbose


### Python API

import py_github_analyzer as pga

Simple analysis (auto-detects environment variables)
result = pga.analyze_repository('https://github.com/user/repo')

Async analysis (recommended for better performance)
result = await pga.analyze_repository_async('https://github.com/user/repo')

With explicit GitHub token
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

Class-based usage
analyzer = pga.GitHubRepositoryAnalyzer(token='ghp_your_token_here')
result = await analyzer.analyze_repository('https://github.com/user/repo')


## 🔑 GitHub Token Setup

The analyzer automatically detects GitHub tokens from multiple sources:

### Priority Order:
1. **`--github-token` parameter** (highest priority)
2. **`GITHUB_TOKEN` environment variable** 
3. **`GH_TOKEN` environment variable** (GitHub CLI compatible)
4. **Anonymous access** (rate limited)

### Setting Up Environment Variables:

**Linux/macOS:**
export GITHUB_TOKEN=ghp_your_token_here
py-github-analyzer https://github.com/user/repo


**Windows (Command Prompt):**
set GITHUB_TOKEN=ghp_your_token_here
py-github-analyzer https://github.com/user/repo


**Windows (PowerShell):**
$env:GITHUB_TOKEN="ghp_your_token_here"
py-github-analyzer https://github.com/user/repo


### Creating a GitHub Token:

1. Visit [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Select **`repo`** scope for private repository access
4. Copy the generated token (starts with `ghp_`)
5. Set it as an environment variable or use as parameter

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
-t, --github-token TOKEN GitHub personal access token
-m, --method METHOD Analysis method: auto, api, zip (default: auto)
-v, --verbose Enable verbose output
--dry-run Simulate analysis without processing
--no-fallback Disable fallback mode on errors
--version Show version information


### Python API Options
await pga.analyze_repository_async(
repo_url='https://github.com/user/repo',
output_dir='./results', # Output directory
output_format='both', # json, bin, both
github_token=None, # Auto-detected if None
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

### Rate Limits
- **Without token**: 60 requests/hour
- **With token**: 5,000 requests/hour  
- **Smart detection**: Automatic rate limit management

## 🛡️ Error Handling

### Robust Error Management
- **Rate limit handling** - Automatic retry with exponential backoff
- **Network resilience** - Multiple fallback strategies
- **Partial analysis** - Continue processing on individual file errors
- **Graceful degradation** - Fallback mode for critical failures
- **Clear error messages** - Actionable error descriptions

### Exit Codes
- **0** - Success
- **1** - Error (validation, network, etc.)
- **2** - Success with warnings (fallback mode)
- **130** - Interrupted by user (Ctrl+C)

## 📋 Examples

### Analyzing Popular Repositories
Large open source project
py-github-analyzer https://github.com/microsoft/vscode

Python project with dependencies
py-github-analyzer https://github.com/requests/requests

JavaScript/Node.js project
py-github-analyzer https://github.com/facebook/react

Private repository (requires token)
export GITHUB_TOKEN=ghp_your_token_here
py-github-analyzer https://github.com/your-org/private-repo


### Batch Processing
import py_github_analyzer as pga
import asyncio

async def analyze_multiple_repos():
repos = [
'https://github.com/user/repo1',
'https://github.com/user/repo2',
'https://github.com/user/repo3'
]

tasks = [pga.analyze_repository_async(repo) for repo in repos]
results = await asyncio.gather(*tasks)

for i, result in enumerate(results):
    print(f"Repository {i+1}: {result['metadata']['repo']}")
    print(f"  Language: {result['metadata']['lang']}")
    print(f"  Files: {len(result['files'])}")
Run batch analysis
asyncio.run(analyze_multiple_repos())


## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
git clone https://github.com/creatorjun/py-github-analyzer.git
cd py-github-analyzer
pip install -e .[dev]


## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📚 Changelog

### v1.0.0 (Latest)
- 🎉 **Initial stable release**
- 🚀 **Pure async architecture** for maximum performance
- 🔐 **Automatic token detection** from environment variables
- 📊 **Comprehensive repository analysis** with metadata generation
- 🌍 **Cross-platform support** (Windows, macOS, Linux)
- ⚡ **High-performance ZIP-first strategy**
- 🛡️ **Robust error handling** and fallback modes
- 💡 **Intelligent file filtering** and dependency detection

---

## 🔗 Links

- **PyPI**: https://pypi.org/project/py-github-analyzer/
- **GitHub**: https://github.com/creatorjun/py-github-analyzer
- **Documentation**: https://github.com/creatorjun/py-github-analyzer#readme
- **Issues**: https://github.com/creatorjun/py-github-analyzer/issues

---

**Built with ❤️ by [Han Jun-hee](https://github.com/creatorjun)**