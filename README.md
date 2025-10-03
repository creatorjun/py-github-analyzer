# py-github-analyzer

<div align="center">

🚀 **AI-optimized GitHub repository analyzer with enhanced private repository support**

[![PyPI version](https://badge.fury.io/py/py-github-analyzer.svg)](https://badge.fury.io/py/py-github-analyzer)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/creatorjun/py-github-analyzer.svg)](https://github.com/creatorjun/py-github-analyzer/stargazers)

**Version 1.0.0 - Official Release with ZIP-First Strategy & Enhanced Private Repository Support**

</div>

---

## ✨ **What's New in v1.0.0**

🎯 **ZIP-First Access Strategy** - Optimized performance with intelligent fallback  
🔒 **Enhanced Private Repository Support** - Smart detection with user-friendly guidance  
⚡ **Advanced Async Processing** - Up to 100 concurrent connections for lightning-fast analysis  
🛡️ **Comprehensive Error Handling** - Clear, actionable error messages and solutions  
🔧 **Intelligent Method Selection** - Auto-detects best approach based on repository and token status

---

## 🚀 **Quick Start**

### Installation
Basic installation (core features)
pip install py-github-analyzer

Full installation (async support for better performance)
pip install py-github-analyzer[async]

OR
pip install py-github-analyzer httpx aiofiles


### Simple Usage
import py_github_analyzer as pga

Public repository (ZIP-first strategy)
result = pga.analyze_repository("https://github.com/python/cpython")
print(f"Languages: {result['metadata']['lang']}")
print(f"Files: {result['metadata']['files']}")

Private repository (automatic API fallback)
result = pga.analyze_repository(
"https://github.com/user/private-repo",
github_token="your_github_token"
)


---

## 🏆 **Key Features**

### 🎯 **Optimized Access Strategy**
- **ZIP-first approach**: Fast bulk download for public repositories
- **Intelligent fallback**: Automatic API method for private repositories  
- **Smart detection**: Distinguishes between private and non-existent repositories

### ⚡ **High-Performance Processing**
- **Native async support**: Up to 100 concurrent connections
- **Parallel processing**: Analyze multiple repositories simultaneously
- **Memory efficient**: Streaming downloads and batch processing

### 🔒 **Private Repository Excellence** 
- **Smart detection**: Clear guidance when private repositories are encountered
- **Token management**: Automatic rate limit optimization (60 → 5000/hour)
- **User-friendly errors**: Step-by-step token setup instructions

### 🤖 **AI-Optimized Output**
- **Structured data**: Perfect for machine learning applications
- **Multiple formats**: JSON (human-readable) and compressed binary (AI-optimized)
- **Language detection**: Automatic programming language identification
- **File prioritization**: Important files processed first

---

## 💡 **Usage Examples**

### Basic Repository Analysis
import py_github_analyzer as pga

Analyze any public repository
result = pga.analyze_repository("https://github.com/microsoft/vscode")
print(f"Repository: {result['metadata']['repo']}")
print(f"Languages: {result['metadata']['lang']}")
print(f"Files analyzed: {result['metadata']['files']}")


### Private Repository Access
import py_github_analyzer as pga

Private repository with token
result = pga.analyze_repository(
"https://github.com/user/private-repo",
github_token="ghp_your_token_here",
output_format="both" # JSON + compressed binary
)


### High-Performance Async Analysis
import asyncio
import py_github_analyzer as pga

async def analyze_multiple_repos():
repos = [
"https://github.com/python/cpython",
"https://github.com/microsoft/vscode",
"https://github.com/tensorflow/tensorflow"
]

# Concurrent analysis
tasks = [pga.analyze_repository_async(repo) for repo in repos]
results = await asyncio.gather(*tasks)

for result in results:
    print(f"✅ {result['metadata']['repo']}: {result['metadata']['files']} files")

return results
Run async analysis
results = asyncio.run(analyze_multiple_repos())


### Object-Oriented Approach
import py_github_analyzer as pga

Create analyzer instance
analyzer = pga.GitHubAnalyzer(token="your_github_token")

Custom analysis
result = analyzer.analyze_repository(
"https://github.com/user/repo",
output_dir="./custom-results",
output_format="json", # Human-readable output
method="zip", # Force ZIP method
verbose=True # Detailed logging
)

print(f"Analysis saved to: {result['output_paths']}")


---

## 🔧 **Command Line Interface**

### Basic Usage
Analyze public repository
py-github-analyzer https://github.com/user/repo

Private repository with token
py-github-analyzer https://github.com/user/private-repo --github-token YOUR_TOKEN

Custom options
py-github-analyzer https://github.com/user/repo
--output-dir ./results
--output-format both
--method auto
--verbose


### Advanced CLI Features
Test repository access (dry run)
py-github-analyzer https://github.com/user/repo --dry-run

Force specific method
py-github-analyzer https://github.com/user/large-repo --method zip

Check system capabilities
py-github-analyzer --check-features

Show comprehensive examples
py-github-analyzer --show-examples


---

## 🔑 **Private Repository Setup**

### Quick Token Setup
1. **Visit**: [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. **Click**: "Generate new token (classic)"
3. **Select**: "repo" scope for private repository access
4. **Copy**: Your token (starts with `ghp_` or `github_pat_`)
5. **Use**: `py-github-analyzer [URL] --github-token YOUR_TOKEN`

### Token Formats
- **Classic**: `ghp_xxxxxxxxxxxxxxxxxxxx`
- **Fine-grained**: `github_pat_xxxxxxxxxxxxxxxxxx`

### Error Handling
The tool provides clear, actionable guidance when private repositories are encountered:
🔒 Private Repository Detected!

📋 Steps to get a token:

Visit: https://github.com/settings/tokens

Click 'Generate new token (classic)'

Select 'repo' scope for private repository access

Copy the generated token

Re-run your command with the token

💡 Example:
py-github-analyzer https://github.com/user/private-repo --github-token YOUR_TOKEN


---

## 📊 **Output Formats**

### JSON Format (Human-readable)
result = pga.analyze_repository(repo_url, output_format="json")

Creates: owner_repo_code.json, owner_repo_meta.json
text

### Binary Format (AI-optimized)
result = pga.analyze_repository(repo_url, output_format="bin") # Default

Creates: owner_repo_code.json.gz, owner_repo_meta.json

### Both Formats
result = pga.analyze_repository(repo_url, output_format="both")

Creates: JSON + compressed binary versions

---

## 🔍 **Analysis Methods**

| Method | Best For | Speed | Token Required |
|--------|----------|--------|----------------|
| `auto` | **All repositories** (recommended) | ⚡⚡⚡ | Optional |
| `zip` | Large public repositories | ⚡⚡⚡ | No |
| `api` | Private repositories, small repos | ⚡⚡ | For private |

### Method Selection Logic
auto method (recommended):
├── Public Repository → ZIP download (fastest)
├── Private Repository + Token → API method
└── Private Repository + No Token → User guidance


---

## ⚡ **Performance Features**

### Async Support
- **Concurrent processing**: Up to 100 simultaneous connections
- **Parallel analysis**: Multiple repositories at once
- **Efficient memory usage**: Streaming and batching

### Optimization Features
- **ZIP streaming**: Memory-efficient large file handling
- **Smart caching**: Optimized repeated operations  
- **Rate limit management**: Automatic optimization
- **Connection pooling**: Reused HTTP connections

---

## 🛠️ **Requirements**

### Core Requirements
- **Python**: 3.7+ (3.8+ recommended for full async support)
- **requests**: >=2.28.0 (HTTP client)
- **rich**: >=13.0.0 (terminal output)

### Optional (High-Performance)
- **httpx**: >=0.24.0 (async HTTP client)
- **aiofiles**: >=0.8.0 (async file operations)

### Installation Options
Minimal installation
pip install py-github-analyzer

Full performance installation
pip install py-github-analyzer[async]

Manual async dependencies
pip install httpx aiofiles


---

## 🧪 **Development**

### Setup Development Environment
Clone repository
git clone https://github.com/creatorjun/py-github-analyzer.git
cd py-github-analyzer

Install with development dependencies
pip install -r requirements-dev.txt

Run tests
pytest tests/ -v

Run async tests
pytest tests/ -v --asyncio-mode=auto

Code formatting
black .
isort .

Type checking
mypy py_github_analyzer/


### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## 📈 **Changelog**

### v1.0.0 - Official Release (2025-10-04)
- 🎯 **ZIP-first access strategy** for optimal performance
- 🔒 **Enhanced private repository detection** with smart user guidance  
- ⚡ **Advanced async processing** with up to 100 concurrent connections
- 🛡️ **Comprehensive error handling** with actionable solutions
- 🔧 **Intelligent method selection** based on repository and token status
- 📚 **Enhanced CLI** with dry-run, feature checking, and examples
- 🤖 **AI-optimized output formats** for machine learning applications
- 📊 **Advanced logging and monitoring** with structured output

---

## 📞 **Support**

- **GitHub**: [https://github.com/creatorjun/py-github-analyzer](https://github.com/creatorjun/py-github-analyzer)
- **Issues**: Report bugs and request features on GitHub
- **PyPI**: [https://pypi.org/project/py-github-analyzer/](https://pypi.org/project/py-github-analyzer/)
- **Email**: createbrain2heart@gmail.com

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by [Han Jun-hee](https://github.com/creatorjun)**

⭐ **Star this repo if you find it useful!** ⭐

</div>