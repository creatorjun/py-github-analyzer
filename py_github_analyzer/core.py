"""
GitHub Repository Analyzer Core Module
High-performance async-first GitHub repository analysis
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config import Config
from .utils import URLParser, TokenUtils
from .logger import get_logger, AnalyzerLogger
from .exceptions import *
from .async_github_client import AsyncGitHubClient
from .metadata_generator import MetadataGenerator
from .file_processor import FileProcessor

class EmptyRepositoryError(GitHubAnalyzerError):
    """Raised when repository exists but contains no analyzable files"""
    pass

class GitHubRepositoryAnalyzer:
    """High-performance async GitHub repository analyzer"""
    
    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        """Initialize analyzer with optional token and logger"""
        # Auto-detect token from environment if not provided
        self.token = TokenUtils.get_github_token(token) if TokenUtils else token
        self.logger = logger or get_logger()
        self.client = AsyncGitHubClient(self.token, self.logger)
        self.metadata_generator = MetadataGenerator()
        self.file_processor = FileProcessor(self.logger)
        
        # Log token status
        if self.token:
            try:
                token_info = TokenUtils.get_token_info(self.token) if TokenUtils else {}
                if token_info:
                    self.logger.info(f"ℹ️  GitHub token loaded: {token_info.get('masked', 'provided')} ({token_info.get('type', 'unknown')})")
                else:
                    self.logger.info(f"ℹ️  GitHub token loaded: provided")
            except Exception:
                self.logger.info(f"ℹ️  GitHub token loaded: provided")
        else:
            self.logger.warning("⚠️  No GitHub token - rate limited to 60 requests/hour")

    async def analyze_repository_async(
        self,
        repo_url: str,
        output_dir: str = "./results",
        output_format: str = "both",
        method: str = "auto",
        verbose: bool = False,
        dry_run: bool = False,
        fallback: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze a GitHub repository asynchronously
        
        Args:
            repo_url: GitHub repository URL
            output_dir: Output directory for results
            output_format: Output format ("json", "bin", or "both")
            method: Analysis method ("auto", "api", or "zip")
            verbose: Enable verbose logging
            dry_run: Simulate analysis without actual processing
            fallback: Enable fallback mode on errors
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Parse repository URL
            url_info = URLParser.parse_github_url(repo_url)
            owner = url_info['owner']
            repo = url_info['repo']
            
            if verbose:
                self.logger.info(f"📂 Analyzing repository: {owner}/{repo}")
                self.logger.info(f"🎯 Method: {method}")
                self.logger.info(f"📁 Output: {output_dir}")
                self.logger.info(f"📄 Format: {output_format}")
                
            if dry_run:
                self.logger.info("🏃 Dry-run mode: Simulating analysis...")
                return {
                    'success': True,
                    'dry_run': True,
                    'repository': f"{owner}/{repo}",
                    'metadata': {
                        'repo': f"{owner}/{repo}",
                        'owner': owner,
                        'name': repo,
                        'lang': ['Simulated'],
                        'size': 'Unknown'
                    },
                    'files': [],
                    'output_paths': {},
                    'fallback_mode': False
                }
            
            # 🔧 올바른 메서드명 사용
            async with self.client:
                if method == "zip" or (method == "auto" and not self.token):
                    # ZIP 방식 사용
                    files = await self.client.download_repository_zip(owner, repo)
                else:
                    # API 방식 사용 - 두 단계로 처리
                    file_tree = await self.client.get_repository_tree_api(owner, repo)
                    files = await self.client.download_files_concurrently(file_tree)
                    
            if not files:
                self.logger.warning(f"⚠️  No files extracted from repository: {repo_url}")
                if fallback:
                    self.logger.warning("⚠️  Using fallback analysis mode...")
                    return await self._fallback_analysis(owner, repo, output_dir, output_format)
                else:
                    raise EmptyRepositoryError(f"No files found in repository {owner}/{repo}")
            
            # 🔧 올바른 메서드명 사용
            processed_files = await self.file_processor.process_files_async(files)
            
            if not processed_files:
                self.logger.warning("⚠️  No valid files to process")
                if fallback:
                    return await self._fallback_analysis(owner, repo, output_dir, output_format)
                else:
                    raise EmptyRepositoryError("No processable files found")
            
            # Generate metadata
            metadata = await self.metadata_generator.generate_metadata_async(
                owner, repo, processed_files
            )
            
            # Calculate statistics
            total_lines = sum(f.get('lines', 0) for f in processed_files if isinstance(f, dict))
            total_size = sum(len(f.get('content', '')) for f in processed_files if isinstance(f, dict))
            
            self.logger.info(f"ℹ️  Analysis completed: {len(processed_files)} files, {total_lines:,} lines")
            self.logger.info(f"ℹ️  Primary language: {metadata.get('lang', ['Unknown'])[0] if metadata.get('lang') else 'Unknown'}")
            
            # Save output
            output_paths = await self._save_output_async(
                output_dir, output_format, metadata, processed_files, f"{owner}_{repo}"
            )
            
            return {
                'success': True,
                'repository': f"{owner}/{repo}",
                'metadata': metadata,
                'files': processed_files,
                'output_paths': output_paths,
                'statistics': {
                    'total_files': len(processed_files),
                    'total_lines': total_lines,
                    'total_size': total_size
                },
                'fallback_mode': False
            }
            
        except Exception as e:
            self.logger.error(f"❌ Unexpected error during async processing: {e}")
            
            if fallback and not isinstance(e, (ValidationError, AuthenticationError)):
                try:
                    url_info = URLParser.parse_github_url(repo_url)
                    return await self._fallback_analysis(
                        url_info['owner'], url_info['repo'], output_dir, output_format
                    )
                except Exception as fallback_error:
                    self.logger.error(f"❌ Fallback analysis also failed: {fallback_error}")
            
            return {
                'success': False,
                'error_message': str(e),
                'repository': repo_url,
                'fallback_mode': False
            }
    
    async def _fallback_analysis(
        self, owner: str, repo: str, output_dir: str, output_format: str
    ) -> Dict[str, Any]:
        """Perform fallback analysis with basic repository information"""
        try:
            # Try to get basic repo info
            async with self.client:
                repo_info = await self.client.get_repository_info(owner, repo, safe_mode=True)
            
            metadata = {
                'repo': f"{owner}/{repo}",
                'owner': owner,
                'name': repo,
                'lang': [repo_info.get('language') or 'Unknown'],
                'size': repo_info.get('size', 0),
                'description': repo_info.get('description', ''),
                'stars': repo_info.get('stargazers_count', 0),
                'forks': repo_info.get('forks_count', 0),
                'created_at': repo_info.get('created_at', ''),
                'updated_at': repo_info.get('updated_at', ''),
                'deps': []
            }
            
            # Save minimal output
            output_paths = await self._save_output_async(
                output_dir, output_format, metadata, [], f"{owner}_{repo}"
            )
            
            return {
                'success': True,
                'repository': f"{owner}/{repo}",
                'metadata': metadata,
                'files': [],
                'output_paths': output_paths,
                'fallback_mode': True,
                'warning': 'Limited analysis - could not access repository files'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error_message': f"Complete analysis failure: {str(e)}",
                'repository': f"{owner}/{repo}",
                'fallback_mode': True
            }
    
    async def _save_output_async(
        self, output_dir: str, output_format: str, metadata: Dict, files: List, prefix: str
    ) -> Dict[str, str]:
        """Save analysis output in specified format"""
        import json
        import pickle
        from pathlib import Path
        
        output_paths = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if output_format in ["json", "both"]:
                json_path = output_path / f"{prefix}_analysis.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'metadata': metadata,
                        'files': files,
                        'generated_at': str(Path().cwd()),
                        'version': Config.VERSION
                    }, f, indent=2, ensure_ascii=False)
                output_paths['json'] = str(json_path)
                
            if output_format in ["bin", "both"]:
                bin_path = output_path / f"{prefix}_analysis.pkl"
                with open(bin_path, 'wb') as f:
                    pickle.dump({
                        'metadata': metadata,
                        'files': files,
                        'generated_at': str(Path().cwd()),
                        'version': Config.VERSION
                    }, f)
                output_paths['bin'] = str(bin_path)
                
        except Exception as e:
            self.logger.warning(f"⚠️  Could not save output files: {e}")
            
        return output_paths

# Convenience async function
async def analyze_repository_async(
    repo_url: str,
    output_dir: str = "./results", 
    output_format: str = "both",
    github_token: Optional[str] = None,
    method: str = "auto",
    verbose: bool = False,
    dry_run: bool = False,
    fallback: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Async convenience function for repository analysis
    
    Args:
        repo_url: GitHub repository URL
        output_dir: Output directory
        output_format: Output format ("json", "bin", "both")
        github_token: GitHub token (auto-detected if None)
        method: Analysis method ("auto", "api", "zip")
        verbose: Enable verbose logging
        dry_run: Simulate without processing
        fallback: Enable fallback mode
        
    Returns:
        Analysis results dictionary
    """
    analyzer = GitHubRepositoryAnalyzer(token=github_token)
    return await analyzer.analyze_repository_async(
        repo_url=repo_url,
        output_dir=output_dir,
        output_format=output_format,
        method=method,
        verbose=verbose,
        dry_run=dry_run,
        fallback=fallback,
        **kwargs
    )
