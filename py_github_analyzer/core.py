"""
GitHub Repository Analyzer Core Module
High-performance async-first GitHub repository analysis
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from threading import Lock

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
        self.token = TokenUtils.get_github_token(token)
        self.logger = logger or get_logger()
        self._lock = Lock()
        
        # Log token status
        token_info = TokenUtils.get_token_info(self.token)
        if token_info['status'] == 'provided':
            if token_info['valid']:
                self.logger.info(f"GitHub token loaded: {token_info['masked']} ({token_info['type']})")
            else:
                self.logger.warning(f"GitHub token format may be invalid: {token_info['masked']}")
        else:
            self.logger.info("No GitHub token found (using anonymous access)")
    
    async def analyze_repository(
        self, 
        repo_url: str,
        output_dir: str = "./results",
        output_format: str = "bin",
        github_token: Optional[str] = None,
        method: str = "auto",
        verbose: bool = False,
        dry_run: bool = False,
        fallback: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze GitHub repository and generate structured output"""
        
        # Auto-detect token with priority: parameter > instance token > environment
        active_token = TokenUtils.get_github_token(github_token) or self.token
        
        try:
            parsed_url = URLParser.parse_github_url(repo_url)
            owner, repo = parsed_url['owner'], parsed_url['repo']
        except ValidationError as e:
            raise ValidationError(f"Invalid repository URL: {e}")
        
        if output_format not in Config.OUTPUT_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported output format: {output_format}",
                output_format, Config.OUTPUT_FORMATS
            )
        
        if dry_run:
            self.logger.info("Dry-run mode: Simulating repository analysis")
            return self._simulate_dry_run(owner, repo, output_dir, output_format)
        
        try:
            async with AsyncGitHubClient(active_token, self.logger) as client:
                files, repo_data = await client.analyze_repository(owner, repo, method)
                
                self._validate_analysis_results(files, repo_url, repo_data)
                
                file_processor = FileProcessor(self.logger)
                processed_files, processing_metadata = file_processor.process_files(files)
                
                metadata_generator = MetadataGenerator(self.logger)
                metadata = metadata_generator.generate_metadata(
                    processed_files, processing_metadata, repo_data, repo_url
                )
                compact_metadata = metadata_generator.generate_compact_metadata(
                    processed_files, processing_metadata, repo_data, repo_url
                )
                
                output_paths = self._save_results(
                    processed_files, metadata, compact_metadata, 
                    owner, repo, output_dir, output_format
                )
                
                self._print_analysis_summary(processed_files, metadata, processing_metadata)
                
                return {
                    'metadata': metadata,
                    'compact_metadata': compact_metadata,
                    'files': processed_files,
                    'repo_info': repo_data,
                    'processing_metadata': processing_metadata,
                    'output_paths': output_paths,
                    'success': True
                }
                
        except Exception as e:
            if fallback:
                self.logger.warning(f"Analysis failed: {e}. Using fallback mode.")
                return self._create_empty_repository_result(repo_url, output_dir, output_format, str(e))
            else:
                raise
    
    def _validate_analysis_results(self, files: List[Dict], repo_url: str, repo_data: Dict):
        """Validate analysis results and raise appropriate errors"""
        if not files:
            if repo_data.get('empty_repository', False):
                raise EmptyRepositoryError(f"Repository is empty or contains no analyzable files: {repo_url}")
            else:
                self.logger.warning(f"No files extracted from repository: {repo_url}")
    
    def _simulate_dry_run(self, owner: str, repo: str, output_dir: str, output_format: str) -> Dict[str, Any]:
        """Simulate repository analysis for dry-run mode"""
        return {
            'metadata': {'repo': f'{owner}/{repo}', 'dry_run': True},
            'compact_metadata': {'repo': f'{owner}/{repo}', 'dry_run': True},
            'files': [],
            'repo_info': {'name': repo, 'owner': {'login': owner}},
            'processing_metadata': {'total_files': 0, 'dry_run': True},
            'output_paths': {'metadata': None, 'compact_metadata': None, 'files': None},
            'success': True,
            'dry_run': True
        }
    
    def _create_empty_repository_result(self, repo_url: str, output_dir: str, output_format: str, error_message: str) -> Dict[str, Any]:
        """Create fallback result for failed analysis"""
        try:
            parsed_url = URLParser.parse_github_url(repo_url)
            owner, repo = parsed_url['owner'], parsed_url['repo']
        except:
            owner, repo = "unknown", "unknown"
        
        empty_metadata = {
            "repo": f"{owner}/{repo}",
            "desc": "Repository information unavailable",
            "lang": "Unknown",
            "size": "0KB",
            "files": 0,
            "main": [],
            "deps": [],
            "fallback_mode": True,
            "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        empty_compact_metadata = {
            "repo": f"{owner}/{repo}",
            "lang": "Unknown",
            "size": "0KB", 
            "files": 0,
            "main": [],
            "deps": [],
            "fallback": True
        }
        
        try:
            output_paths = self._save_results(
                [], empty_metadata, empty_compact_metadata,
                owner, repo, output_dir, output_format
            )
        except Exception as save_error:
            self.logger.error(f"Failed to save fallback results: {save_error}")
            output_paths = {}
        
        return {
            'metadata': empty_metadata,
            'compact_metadata': empty_compact_metadata,
            'files': [],
            'repo_info': {'name': repo, 'owner': {'login': owner}},
            'processing_metadata': {'total_files': 0, 'fallback_mode': True},
            'output_paths': output_paths,
            'success': True,
            'fallback_mode': True,
            'error_message': error_message
        }
    
    def _save_results(
        self, 
        processed_files: List[Dict], 
        metadata: Dict, 
        compact_metadata: Dict,
        owner: str, 
        repo: str, 
        output_dir: str, 
        output_format: str
    ) -> Dict[str, str]:
        """Save analysis results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        base_filename = f"{owner}_{repo}"
        output_paths = {}
        
        if output_format in ["json", "both"]:
            metadata_path = output_path / f"{base_filename}_meta.json"
            compact_path = output_path / f"{base_filename}_compact_meta.json"
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            with open(compact_path, 'w', encoding='utf-8') as f:
                json.dump(compact_metadata, f, ensure_ascii=False)
            
            output_paths['metadata'] = str(metadata_path)
            output_paths['compact_metadata'] = str(compact_path)
        
        if output_format in ["bin", "both"] and processed_files:
            files_data = {"f": {file_info['path']: file_info['content'] for file_info in processed_files if file_info.get('path') and file_info.get('content')}}
            
            code_path = output_path / f"{base_filename}_code.json"
            with open(code_path, 'w', encoding='utf-8') as f:
                json.dump(files_data, f, ensure_ascii=False)
            
            output_paths['files'] = str(code_path)
        
        return output_paths
    
    def _print_analysis_summary(self, files: List[Dict], metadata: Dict, processing_metadata: Dict):
        """Print analysis summary"""
        total_files = len(files)
        total_lines = sum(f.get('lines', 0) for f in files)
        languages = metadata.get('lang', [])
        
        self.logger.info(f"Analysis completed: {total_files} files, {total_lines:,} lines")
        if languages:
            self.logger.info(f"Primary language: {languages[0]}")
        
        deps = metadata.get('deps', [])
        if deps:
            self.logger.info(f"Dependencies found: {len(deps)}")


# Global convenience functions
async def analyze_repository_async(
    repo_url: str,
    output_dir: str = "./results", 
    output_format: str = "bin",
    github_token: Optional[str] = None,
    method: str = "auto",
    verbose: bool = False,
    dry_run: bool = False,
    fallback: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Async convenience function for repository analysis"""
    # Auto-detect token if not provided
    active_token = TokenUtils.get_github_token(github_token)
    
    analyzer = GitHubRepositoryAnalyzer(token=active_token)
    if verbose:
        from .logger import set_verbose
        set_verbose(True)
    
    return await analyzer.analyze_repository(
        repo_url=repo_url,
        output_dir=output_dir,
        output_format=output_format,
        github_token=github_token,
        method=method,
        verbose=verbose,
        dry_run=dry_run,
        fallback=fallback
    )

def analyze_repository(
    repo_url: str,
    output_dir: str = "./results",
    output_format: str = "bin",
    github_token: Optional[str] = None,
    method: str = "auto",
    verbose: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Sync wrapper around async analysis function"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError(
                "Cannot use sync wrapper inside async context. "
                "Use 'analyze_repository_async' instead."
            )
    except RuntimeError:
        pass
    
    return asyncio.run(analyze_repository_async(
        repo_url=repo_url,
        output_dir=output_dir,
        output_format=output_format,
        github_token=github_token,
        method=method,
        verbose=verbose,
        **kwargs
    ))
