#!/usr/bin/env python3
"""
GitHub Repository Analyzer Core Module
High-performance async-first GitHub repository analysis
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiofiles
import json

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
        self.token = TokenUtils.get_github_token(token) if TokenUtils else token
        self.logger = logger or get_logger()
        self.client = AsyncGitHubClient(self.token, self.logger)
        self.metadata_generator = MetadataGenerator()
        self.file_processor = FileProcessor(self.logger)
        
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
            output_format: Output format ('json', 'bin', or 'both')
            method: Analysis method ('auto', 'api', or 'zip')
            verbose: Enable verbose logging
            dry_run: Simulate analysis without actual processing
            fallback: Enable fallback mode on errors
            
        Returns:
            Dict containing analysis results
        """
        try:
            url_info = URLParser.parse_github_url(repo_url)
            owner = url_info['owner']
            repo = url_info['repo']
            
            if verbose:
                self.logger.info(f"ℹ️  📂 Analyzing repository: {owner}/{repo}")
                self.logger.info(f"ℹ️  🎯 Method: {method}")
                self.logger.info(f"ℹ️  📁 Output: {output_dir}")
                self.logger.info(f"ℹ️  📄 Format: {output_format}")
                
            if dry_run:
                self.logger.info(f"ℹ️  🏃 Dry-run mode: Simulating analysis...")
                return {
                    'success': True,
                    'dry_run': True,
                    'repository': f'{owner}/{repo}',
                    'metadata': {
                        'repo': f'{owner}/{repo}',
                        'owner': owner,
                        'name': repo,
                        'lang': ['Simulated'],
                        'size': 'Unknown'
                    },
                    'files': [],
                    'output_paths': {},
                    'fallback_mode': False
                }
            
            # Select analysis method with ZIP-first strategy
            if method == 'api' or (method == 'auto' and self.token):
                try:
                    files = await self.client.get_files_from_api(owner, repo)
                except Exception as e:
                    if method == 'auto':
                        self.logger.warning(f"⚠️  API failed, falling back to ZIP: {e}")
                        files = await self.client.get_files_from_zip(owner, repo)
                    else:
                        raise
            else:
                files = await self.client.get_files_from_zip(owner, repo)
            
            if not files:
                self.logger.warning(f"⚠️  No files extracted from repository: {repo_url}")
                if fallback:
                    self.logger.warning("⚠️  Using fallback analysis mode...")
                    return await self._fallback_analysis(owner, repo, output_dir, output_format)
                else:
                    raise EmptyRepositoryError(f"No files found in repository: {owner}/{repo}")
            
            # Process files using thread pool for CPU-intensive work
            processed_files = await asyncio.to_thread(self.file_processor.process_files, files)
            
            if not processed_files:
                self.logger.warning("⚠️  No valid files to process")
                if fallback:
                    return await self._fallback_analysis(owner, repo, output_dir, output_format)
                else:
                    raise EmptyRepositoryError("No processable files found")
            
            # Get additional repository info for metadata
            repo_info = {}
            processing_metadata = {}
            try:
                repo_info = await self.client.get_repository_info(owner, repo)
                processing_metadata = {
                    'method': method,
                    'files_count': len(processed_files),
                    'processing_time': 0,
                }
            except Exception as e:
                self.logger.warning(f"⚠️  Could not fetch repository info: {e}")
            
            # Generate metadata using thread pool
            metadata = await asyncio.to_thread(
                self.metadata_generator.generate_metadata,
                processed_files,
                processing_metadata,
                repo_info,
                repo_url
            )
            
            total_lines = sum(f.get('lines', 0) for f in processed_files if isinstance(f, dict))
            
            self.logger.info(f"✅ Analysis completed: {len(processed_files)} files, {total_lines:,} lines")
            self.logger.info(f"🗣️  Primary language: {metadata.get('lang', ['Unknown'])[0] if metadata.get('lang') else 'Unknown'}")
            
            # Save output files
            output_paths = await self._save_output_async(
                output_dir, output_format, metadata, processed_files, f'{owner}_{repo}'
            )
            
            return {
                'success': True,
                'repository': f'{owner}/{repo}',
                'metadata': metadata,
                'files': processed_files,
                'output_paths': output_paths,
                'fallback_mode': False
            }
            
        except Exception as e:
            self.logger.error(f"❌ ❌ Unexpected error during async processing: {e}")
            if fallback:
                self.logger.warning("⚠️  Attempting fallback analysis...")
                try:
                    url_info = URLParser.parse_github_url(repo_url)
                    return await self._fallback_analysis(url_info['owner'], url_info['repo'], output_dir, output_format)
                except Exception as fallback_error:
                    self.logger.error(f"❌ Fallback analysis also failed: {fallback_error}")
            
            return {
                'success': False,
                'error_message': str(e),
                'repository': repo_url,
                'fallback_mode': fallback
            }
    
    async def _fallback_analysis(self, owner: str, repo: str, output_dir: str, output_format: str) -> Dict[str, Any]:
        """Provide basic fallback analysis when normal processing fails"""
        try:
            repo_info = await self.client.get_repository_info(owner, repo)
            
            fallback_metadata = {
                'repo': f'{owner}/{repo}',
                'owner': owner,
                'name': repo,
                'description': repo_info.get('description', 'No description available'),
                'lang': ['Unknown'],
                'size': repo_info.get('size', 0),
                'created': repo_info.get('created_at', 'Unknown'),
                'updated': repo_info.get('updated_at', 'Unknown'),
                'stars': repo_info.get('stargazers_count', 0),
                'forks': repo_info.get('forks_count', 0),
                'fallback_mode': True,
                'analysis_mode': 'basic_metadata_only'
            }
            
            output_paths = await self._save_output_async(
                output_dir, output_format, fallback_metadata, [], f'{owner}_{repo}_fallback'
            )
            
            self.logger.warning("⚠️  Fallback analysis completed with limited data")
            
            return {
                'success': True,
                'repository': f'{owner}/{repo}',
                'metadata': fallback_metadata,
                'files': [],
                'output_paths': output_paths,
                'fallback_mode': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Fallback analysis failed: {e}")
            return {
                'success': False,
                'error_message': f"Fallback analysis failed: {e}",
                'repository': f'{owner}/{repo}',
                'fallback_mode': True
            }
    
    async def _save_output_async(
        self, 
        output_dir: str, 
        output_format: str, 
        metadata: Dict[str, Any], 
        files: List[Dict[str, Any]], 
        filename_prefix: str
    ) -> Dict[str, str]:
        """Save analysis results asynchronously"""
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        output_paths = {}
        
        if output_format in ['json', 'both']:
            json_path = output_dir_path / f"{filename_prefix}.json"
            output_data = {
                'metadata': metadata,
                'files': files
            }
            
            async with aiofiles.open(json_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(output_data, indent=2, ensure_ascii=False))
            
            output_paths['json'] = str(json_path)
        
        if output_format in ['bin', 'both']:
            bin_path = output_dir_path / f"{filename_prefix}.bin"
            output_data = {
                'metadata': metadata,
                'files': files
            }
            
            async with aiofiles.open(bin_path, 'wb') as f:
                import pickle
                await f.write(pickle.dumps(output_data))
            
            output_paths['bin'] = str(bin_path)
        
        return output_paths


async def analyze_repository_async(repo_url: str, **kwargs) -> Dict[str, Any]:
    """Standalone async function for repository analysis"""
    analyzer = GitHubRepositoryAnalyzer()
    return await analyzer.analyze_repository_async(repo_url, **kwargs)
