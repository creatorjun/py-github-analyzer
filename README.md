# 🚀 py-github-analyzer

High-performance async GitHub repository analyzer with AI-optimized code extraction and smart .env file support

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/py-github-analyzer.svg)](https://badge.fury.io/py/py-github-analyzer)

## ✨ Features

### 🔐 **Advanced Authentication**
- **✅ Fine-grained Token Support**: Latest GitHub token standard with `Bearer` authentication
- **✅ Classic Token Support**: Traditional `ghp_` tokens with `token` authentication  
- **🔄 Auto Token Detection**: Automatically detects token type and uses appropriate authentication
- **📁 Multi-source Token Loading**: Environment variables, .env files, CLI parameters
- **🔒 Private Repository Access**: Full access to private repositories with proper permissions

### ⚡ **High Performance**
- **🎯 ZIP-first Strategy**: Optimal download method with intelligent API fallback
- **📊 Smart Rate Limit Management**: Adaptive strategies for different token types
- **🚀 Pure Async Architecture**: Built with modern async/await patterns for maximum performance
- **🔄 Intelligent Fallback**: Graceful degradation when ZIP access fails

### 📋 **Smart Analysis**
- **🔍 Automatic Language Detection**: Accurate detection and dependency mapping
- **📊 Intelligent File Filtering**: Skip binaries, focus on source code with priority scoring
- **📦 Multiple Output Formats**: JSON metadata and structured code extraction
- **🎯 Framework Detection**: Identifies popular frameworks and patterns

### 🌐 **Cross-Platform**
- **💻 Windows, macOS, and Linux**: Full compatibility across all platforms
- **🛡️ Smart Error Handling**: Comprehensive error messages and recovery strategies
- **📁 Smart .env Support**: Automatically finds and loads tokens from .env files

## 📦 Installation

### From PyPI (Recommended)

pip install py-github-analyzer


### From Source

git clone https://github.com/creatorjun/py-github-analyzer.git
cd py-github-analyzer
pip install -e .


## 🔑 GitHub Token Setup (Recommended)

### Supported Token Types

py-github-analyzer supports **all GitHub token types** with automatic detection:

#### 🔑 **Fine-grained Personal Access Tokens** (Latest)
- **Prefix**: `github_pat_`
- **Authentication**: `Bearer` header
- **Permissions**: Repository-specific granular access
- **Security**: ✅ Enhanced security with minimal required permissions
- **Performance**: ⚠️ API-only access for private repos (ZIP may fail)
- **Setup**: GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens

#### 🔑 **Classic Personal Access Tokens** (Traditional)
- **Prefix**: `ghp_`
- **Authentication**: `token` header  
- **Permissions**: Broad scope-based access
- **Security**: ⚠️ Wide access permissions
- **Performance**: ✅ Full ZIP and API access
- **Setup**: GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)

### Creating Tokens

#### For Fine-grained Tokens (Recommended for Security):
1. Visit [GitHub Settings → Personal Access Tokens → Fine-grained tokens](https://github.com/settings/personal-access-tokens/new)
2. Select **Repository access**: Choose specific repositories or all repositories
3. Set **Repository permissions**:
   - **Contents**: Read (required for file access)
   - **Actions**: Read (required for ZIP downloads)
   - **Metadata**: Read (required for repository info)
4. Copy the token (starts with `github_pat_`)

#### For Classic Tokens (Faster for Bulk Analysis):
1. Visit [GitHub Settings → Personal Access Tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Select **repo** scope for private repository access
4. Copy the token (starts with `ghp_`)

### Setting Up Your Token

Option 1: Environment Variable (Recommended)
export GITHUB_TOKEN=github_pat_your_token_here

or
export GITHUB_TOKEN=ghp_your_classic_token_here

Option 2: .env file in your project directory
echo "GITHUB_TOKEN=github_pat_your_token_here" > .env

Option 3: CLI parameter
py-github-analyzer https://github.com/owner/repo --github-token github_pat_your_token_here

## 📋 Usage Examples

### Basic Usage

Analyze a public repository
py-github-analyzer https://github.com/octocat/Hello-World

Analyze with verbose output
py-github-analyzer https://github.com/owner/repo --verbose

Specify output directory and format
py-github-analyzer https://github.com/owner/repo --output-dir ./results --output-format json

### Using Fine-grained Tokens

Set Fine-grained token (recommended for security)
export GITHUB_TOKEN=github_pat_your_fine_grained_token

Analyze private repository
py-github-analyzer https://github.com/owner/private-repo --verbose

**Expected output with Fine-grained token:**
🔑 GitHub token loaded: github_pat_...XYZ (fine_grained)
⚡ Rate limit: 5000 requests/hour
🎯 Using ZIP-first strategy (auto mode)
⚠️ ZIP failed, trying API fallback...
📥 Downloading 117 files via API...
📥 Progress: 50/117 files (42.7%)
✅ API fallback successful! (117 files)
✅ Analysis completed: 117 files, 25,847 lines
🗣️ Primary language: Kotlin

### Using Classic Tokens

Set Classic token (recommended for speed)
export GITHUB_TOKEN=ghp_your_classic_token

Same analysis with Classic token (typically faster)
py-github-analyzer https://github.com/owner/private-repo --verbose


**Expected output with Classic token:**
🔑 GitHub token loaded: ghp_...DXg7 (classic)
⚡ Rate limit: 5000 requests/hour
🎯 Using ZIP-first strategy (auto mode)
✅ ZIP download successful! (117 files)
✅ Analysis completed: 117 files, 25,847 lines
🗣️ Primary language: Kotlin


### Advanced Options

Force specific analysis method
py-github-analyzer https://github.com/owner/repo --method api
py-github-analyzer https://github.com/owner/repo --method zip

Multiple output formats
py-github-analyzer https://github.com/owner/repo --output-format both

Dry run (test without processing)
py-github-analyzer https://github.com/owner/repo --dry-run

Enable fallback mode
py-github-analyzer https://github.com/owner/repo --fallback


## 📊 Performance Comparison

### Token Type Performance Analysis

| Token Type | Rate Limit | ZIP Access | API Batch Size | Typical Speed | Best For |
|------------|------------|------------|----------------|---------------|----------|
| **None** | 60/hour | ❌ Public only | N/A | ⚠️ Very Limited | Testing only |
| **Classic** | 5,000/hour | ✅ Full access | 10 files/batch | ⚡ **Fastest** | Bulk analysis |
| **Fine-grained** | 5,000/hour | ⚠️ Often requires API fallback | 3 files/batch | ✅ Good | Secure analysis |

### Performance Optimization Details

#### **🚀 Classic Tokens** (Fastest)
- **ZIP Downloads**: ✅ Direct access to repository archives
- **Batch Processing**: 10 files per API request
- **Rate Limits**: Standard 5,000 requests/hour
- **Typical Analysis Time**: 10-30 seconds for medium repositories

#### **🔐 Fine-grained Tokens** (Secure but Slower)
- **ZIP Downloads**: ⚠️ Often fails, triggers API fallback automatically
- **Batch Processing**: 3 files per API request (to avoid rate limits)
- **Rate Limits**: 5,000 requests/hour (but stricter per-request limits)
- **Typical Analysis Time**: 1-5 minutes for medium repositories
- **Progress Tracking**: Real-time progress indicators for API operations

> **💡 Performance Tip**: For frequent bulk analysis, Classic tokens provide better performance. For security-sensitive environments or specific repository access, Fine-grained tokens offer better permission control.

### Analysis Speed Examples

Repository with 100+ files:
Classic Token: ~15 seconds (ZIP + fast processing)
Fine-grained: ~2 minutes (API fallback + batch limits)
No Token: ❌ Private repos inaccessible

## 🔧 Troubleshooting

### Fine-grained Token Issues

**Problem**: ZIP download fails, API fallback used
❌ ZIP analysis failed: Repository does not exist or is not accessible
📥 Downloading 117 files via API...
✅ API fallback successful! (117 files)


**Solutions**:
1. **Add Actions permission**: Go to [GitHub Settings → Fine-grained tokens](https://github.com/settings/personal-access-tokens) → Edit token → Repository permissions → **Actions: Read**
2. **Accept slower API processing**: Fine-grained tokens often require API-only access for private repositories
3. **Use Classic token for speed**: If you need faster analysis and broader access is acceptable

**Problem**: Very slow analysis with Fine-grained tokens
📥 Progress: 10/117 files (8.5%) [Taking too long...]


**Explanation**: Fine-grained tokens have stricter rate limiting. The analyzer automatically:
- Uses smaller batch sizes (3 vs 10 files per request)
- Adds delays between requests to prevent rate limit hits
- Shows progress indicators for operations taking longer than 30 seconds

**Solutions**:
- **Wait patiently**: Analysis will complete, just slower than Classic tokens
- **Switch to Classic token**: For regular bulk analysis
- **Use `--verbose` flag**: To monitor progress and understand what's happening

### Token Detection Issues

**Problem**: Token not detected from .env file
Check token detection status
py-github-analyzer --version # Should show token status


**Problem**: Wrong token type detected
Override with specific token
py-github-analyzer https://github.com/owner/repo --github-token github_pat_your_token


**Problem**: Rate limit exceeded
❌ Rate limit exceeded. Please wait before retrying.


**Solutions**:
- **Wait**: Rate limits reset every hour
- **Check token type**: Ensure you're using a valid GitHub token
- **Verify permissions**: Ensure token has required repository access

### Common Issues

**Private Repository Access Denied**:
❌ Repository 'owner/private-repo' does not exist or is not accessible.

- Verify token has access to the specific repository
- Check repository name and owner spelling
- Ensure repository hasn't been moved or deleted

**Large Repository Analysis**:
⚠️ Repository too large, this may take several minutes...

- Large repositories (500+ files) may take longer, especially with Fine-grained tokens
- Consider using `--method zip` to force ZIP download (if available)
- Monitor progress with `--verbose` flag

## 📖 Output Format

### JSON Structure

{
"metadata": {
"repo": "owner/repository-name",
"desc": "Repository description",
"lang": ["Primary", "Secondary", "Languages"],
"size": {
"repo_size": "288KB",
"source_size": "294.2KB",
"display_size": "288KB"
},
"files": 117,
"main": ["main.py", "app.py", "index.js"],
"deps": ["dependency1", "dependency2"],
"created": 1634567890,
"version": "1.0.0"
},
"files": [
{
"path": "src/main.py",
"content": "file content here",
"size": 1234,
"lines": 45,
"language": "Python",
"priority": 950
}
]
}


## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

git clone https://github.com/creatorjun/py-github-analyzer.git
cd py-github-analyzer

Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

Install development dependencies
pip install -e .[dev]

Run tests
python -m pytest tests/


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- GitHub API for providing excellent repository access
- The Python async/await ecosystem for enabling high-performance analysis
- All contributors who help improve this tool

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/creatorjun/py-github-analyzer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/creatorjun/py-github-analyzer/discussions)
- **Documentation**: [Wiki](https://github.com/creatorjun/py-github-analyzer/wiki)

---

**Made with ❤️ for developers who need fast, reliable GitHub repository analysis**

*py-github-analyzer v1.0.0 - Supports both Classic and Fine-grained GitHub tokens*