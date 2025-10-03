import re
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict
import hashlib

from .config import Config
from .utils import TextUtils, ValidationUtils
from .logger import AnalyzerLogger


class LanguageDetector:
    """Language and framework detection utilities"""
    
    def __init__(self):
        self.framework_patterns = {
            'python': {
                'django': [
                    r'from django',
                    r'import django',
                    r'DJANGO_SETTINGS_MODULE',
                    r'manage\.py',
                    r'settings\.py'
                ],
                'flask': [
                    r'from flask',
                    r'import flask',
                    r'Flask\(__name__\)',
                    r'@app\.route'
                ],
                'fastapi': [
                    r'from fastapi',
                    r'import fastapi',
                    r'FastAPI\(',
                    r'@app\.(get|post|put|delete)'
                ],
                'pytest': [
                    r'import pytest',
                    r'def test_',
                    r'@pytest\.',
                    r'conftest\.py'
                ]
            },
            'javascript': {
                'react': [
                    r'import.*react',
                    r'from.*react',
                    r'React\.',
                    r'jsx|tsx',
                    r'useState|useEffect'
                ],
                'vue': [
                    r'import.*vue',
                    r'from.*vue',
                    r'Vue\.',
                    r'<template>',
                    r'\.vue'
                ],
                'angular': [
                    r'@angular',
                    r'@Component',
                    r'@Injectable',
                    r'NgModule'
                ],
                'express': [
                    r'require.*express',
                    r'import.*express',
                    r'app\.get|app\.post',
                    r'express\(\)'
                ],
                'nextjs': [
                    r'next/',
                    r'getStaticProps',
                    r'getServerSideProps',
                    r'next\.config'
                ]
            },
            'typescript': {
                'angular': [
                    r'@angular',
                    r'@Component',
                    r'@Injectable'
                ],
                'nestjs': [
                    r'@nestjs',
                    r'@Controller',
                    r'@Injectable',
                    r'@Module'
                ]
            }
        }
    
    # file_processor.py의 detect_languages 메서드 수정
    def detect_languages(self, files: List[Dict[str, Any]]) -> Dict[str, float]:
        """Detect programming languages from file list with size-weighted scoring"""
        language_stats = defaultdict(int)
        total_code_size = 0
        
        # Ensure files is a list
        if not isinstance(files, list):
            return {}
        
        for file_item in files:
            # Ensure each item is a dictionary
            if not isinstance(file_item, dict):
                continue
                
            path = file_item.get('path', '')
            size = file_item.get('size', 0)
            
            # Skip very small files and non-code files
            if size < 10:
                continue
            
            language = Config.get_language_from_extension(path)
            if language != 'unknown':
                language_stats[language] += size
                total_code_size += size
        
        # Convert to percentages and filter significant languages (>= 5%)
        language_percentages = {}
        for language, size in language_stats.items():
            percentage = (size / total_code_size * 100) if total_code_size > 0 else 0
            if percentage >= 5.0:
                language_percentages[language] = round(percentage, 1)
        
        # Sort by percentage
        return dict(sorted(language_percentages.items(), key=lambda x: x[1], reverse=True))

    
    def detect_primary_language(self, files: List[Dict[str, Any]]) -> str:
        """Detect the primary programming language"""
        languages = self.detect_languages(files)
        if not languages:
            return 'unknown'
        return next(iter(languages.keys()))  # First (highest percentage) language
    
    def detect_frameworks(self, files: List[Dict[str, Any]], primary_language: str) -> List[str]:
        """Detect frameworks based on file contents and patterns"""
        if primary_language not in self.framework_patterns:
            return []
        
        framework_scores = defaultdict(int)
        framework_patterns = self.framework_patterns[primary_language]
        
        for file_info in files:
            path = file_info.get('path', '')
            content = file_info.get('content', '')
            
            if not content:
                continue
            
            # Check filename patterns
            filename = Path(path).name.lower()
            
            # Check each framework
            for framework, patterns in framework_patterns.items():
                score = 0
                
                for pattern in patterns:
                    # Check in filename
                    if re.search(pattern, filename, re.IGNORECASE):
                        score += 2
                    
                    # Check in file content (sample first 5000 chars for performance)
                    content_sample = content[:5000]
                    matches = len(re.findall(pattern, content_sample, re.IGNORECASE | re.MULTILINE))
                    score += matches
                
                if score > 0:
                    framework_scores[framework] += score
        
        # Return frameworks with significant scores
        detected_frameworks = []
        for framework, score in framework_scores.items():
            if score >= 3:  # Threshold for detection
                detected_frameworks.append(framework)
        
        # Sort by score
        detected_frameworks.sort(key=lambda x: framework_scores[x], reverse=True)
        return detected_frameworks[:3]  # Return top 3 frameworks


class DependencyExtractor:
    """Extract dependencies from various file types"""
    
    def __init__(self):
        self.extractors = {
            'python': self._extract_python_deps,
            'javascript': self._extract_js_deps,
            'typescript': self._extract_js_deps,  # Same as JS
            'java': self._extract_java_deps,
            'go': self._extract_go_deps,
            'rust': self._extract_rust_deps,
            'csharp': self._extract_csharp_deps
        }
    
    def extract_dependencies(self, files: List[Dict[str, Any]], primary_language: str) -> List[str]:
        """Extract dependencies for the primary language"""
        if primary_language not in self.extractors:
            return []
        
        extractor = self.extractors[primary_language]
        all_deps = set()
        
        for file_info in files:
            try:
                deps = extractor(file_info)
                all_deps.update(deps)
                
                # Limit to prevent excessive memory usage
                if len(all_deps) > 100:
                    break
            except Exception:
                continue  # Skip problematic files
        
        # Filter and clean dependencies
        filtered_deps = []
        for dep in all_deps:
            if len(dep) > 1 and len(dep) < 50 and not dep.startswith('.'):
                filtered_deps.append(dep)
        
        return sorted(filtered_deps)[:30]  # Return top 30
    
    def _extract_python_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Python dependencies"""
        deps = set()
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        
        filename = Path(path).name.lower()
        
        # Handle requirements files
        if filename in ['requirements.txt', 'requirements-dev.txt', 'dev-requirements.txt']:
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Extract package name (before any version specifiers)
                    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if match:
                        deps.add(match.group(1))
        
        # Handle setup.py
        elif filename == 'setup.py':
            # Look for install_requires
            requires_match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if requires_match:
                requires_content = requires_match.group(1)
                for match in re.findall(r'["\']([a-zA-Z0-9_-]+)', requires_content):
                    deps.add(match)
        
        # Handle pyproject.toml
        elif filename == 'pyproject.toml':
            # Simple regex-based extraction (not full TOML parsing)
            deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if deps_match:
                deps_content = deps_match.group(1)
                for match in re.findall(r'["\']([a-zA-Z0-9_-]+)', deps_content):
                    deps.add(match)
        
        # Handle import statements in regular Python files
        elif filename.endswith('.py'):
            # Extract from import statements
            import_pattern = r'(?:^from\s+([a-zA-Z0-9_]+)|^import\s+([a-zA-Z0-9_]+))'
            for match in re.findall(import_pattern, content, re.MULTILINE):
                dep = match[0] or match[1]
                if dep and not dep.startswith('_'):
                    deps.add(dep)
        
        return deps
    
    def _extract_js_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract JavaScript/TypeScript dependencies"""
        deps = set()
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        
        filename = Path(path).name.lower()
        
        # Handle package.json
        if filename == 'package.json':
            try:
                package_data = json.loads(content)
                for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                    if dep_type in package_data:
                        deps.update(package_data[dep_type].keys())
            except json.JSONDecodeError:
                pass
        
        # Handle JavaScript/TypeScript files
        elif filename.endswith(('.js', '.ts', '.jsx', '.tsx')):
            # Extract from import/require statements
            patterns = [
                r'import.*?from\s+[\'"]([^\'\"]+)[\'"]',
                r'require\([\'"]([^\'\"]+)[\'"]\)',
                r'import\([\'"]([^\'\"]+)[\'"]\)',
                r'import\s+[\'"]([^\'\"]+)[\'"]'
            ]
            
            for pattern in patterns:
                for match in re.findall(pattern, content):
                    # Skip relative imports
                    if not match.startswith('.'):
                        # Extract base package name
                        base_pkg = match.split('/')[0]
                        if base_pkg.startswith('@'):
                            # Scoped package
                            parts = match.split('/')
                            if len(parts) >= 2:
                                base_pkg = f"{parts[0]}/{parts[1]}"
                        deps.add(base_pkg)
        
        return deps
    
    def _extract_java_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Java dependencies"""
        deps = set()
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        
        filename = Path(path).name.lower()
        
        # Handle Maven pom.xml
        if filename == 'pom.xml':
            # Extract groupId and artifactId
            artifact_pattern = r'<artifactId>(.*?)</artifactId>'
            for match in re.findall(artifact_pattern, content):
                deps.add(match)
        
        # Handle Gradle build files
        elif filename in ['build.gradle', 'build.gradle.kts']:
            # Extract implementation/compile dependencies
            dep_pattern = r'(?:implementation|compile|api)\s+[\'"]([^:]+):([^:\'\"]+)'
            for match in re.findall(dep_pattern, content):
                deps.add(match[1])  # artifactId
        
        return deps
    
    def _extract_go_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Go dependencies"""
        deps = set()
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        
        filename = Path(path).name.lower()
        
        if filename == 'go.mod':
            # Extract require statements
            require_pattern = r'require\s+([^\s]+)'
            for match in re.findall(require_pattern, content):
                deps.add(match)
        
        elif filename.endswith('.go'):
            # Extract import statements
            import_pattern = r'import\s+(?:"([^"]+)"|`([^`]+)`)'
            for match in re.findall(import_pattern, content):
                dep = match[0] or match[1]
                deps.add(dep)
        
        return deps
    
    def _extract_rust_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Rust dependencies"""
        deps = set()
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        
        filename = Path(path).name.lower()
        
        if filename == 'cargo.toml':
            # Extract dependencies section
            deps_match = re.search(r'\[dependencies\](.*?)(?:\[|$)', content, re.DOTALL)
            if deps_match:
                deps_content = deps_match.group(1)
                for line in deps_content.split('\n'):
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        dep_name = line.split('=')[0].strip()
                        deps.add(dep_name)
        
        return deps
    
    def _extract_csharp_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract C# dependencies"""
        deps = set()
        path = file_info.get('path', '')
        content = file_info.get('content', '')
        
        filename = Path(path).name.lower()
        
        # Handle .csproj files
        if filename.endswith('.csproj'):
            # Extract PackageReference
            package_pattern = r'<PackageReference\s+Include="([^"]+)"'
            for match in re.findall(package_pattern, content):
                deps.add(match)
        
        # Handle packages.config
        elif filename == 'packages.config':
            package_pattern = r'<package\s+id="([^"]+)"'
            for match in re.findall(package_pattern, content):
                deps.add(match)
        
        return deps


class FilePrioritizer:
    """File prioritization and filtering logic"""
    
    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self.logger = logger or AnalyzerLogger()
        self.language_detector = LanguageDetector()
    
    def calculate_enhanced_priority(self, file_info: Dict[str, Any], 
                                   primary_language: str = None,
                                   detected_frameworks: List[str] = None) -> int:
        """Calculate enhanced priority score for file"""
        path = file_info.get('path', '')
        base_priority = Config.get_file_priority(path)
        
        # Language-specific bonus
        if primary_language and primary_language in Config.LANGUAGE_PRIORITY_PATTERNS:
            lang_config = Config.LANGUAGE_PRIORITY_PATTERNS[primary_language]
            
            # Entry point bonus
            filename = Path(path).name
            if filename in lang_config.get('entry_points', []):
                base_priority += 200
            
            # Config file bonus
            elif filename in lang_config.get('config_files', []):
                base_priority += 150
            
            # Important directory bonus
            for dir_pattern in lang_config.get('important_dirs', []):
                if dir_pattern in path:
                    base_priority += 100
                    break
            
            # Framework-specific bonus
            if detected_frameworks:
                framework_files = lang_config.get('framework_files', {})
                for framework in detected_frameworks:
                    if framework in framework_files:
                        for pattern in framework_files[framework]:
                            if pattern in path:
                                base_priority += 200
                                break
        
        # File extension bonus
        ext = Path(path).suffix.lower()
        if ext in Config.EXTENSION_TO_LANGUAGE:
            base_priority += 50
        
        # Penalize deeply nested files
        depth = path.count('/')
        if depth > 4:
            base_priority -= (depth - 4) * 10
        
        # Penalize test files (unless they're really important)
        if '/test' in path.lower() or 'test_' in Path(path).name.lower():
            if base_priority < 500:
                base_priority = max(base_priority - 100, 50)
        
        return max(base_priority, 10)  # Minimum priority
    
    def filter_and_prioritize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter, prioritize, and select optimal set of files"""
        # First pass: basic filtering
        valid_files = self._basic_filter(files)
        
        # Detect primary language and frameworks
        primary_language = self.language_detector.detect_primary_language(valid_files)
        detected_frameworks = self.language_detector.detect_frameworks(valid_files, primary_language)
        
        self.logger.debug(f"Primary language: {primary_language}")
        self.logger.debug(f"Detected frameworks: {detected_frameworks}")
        
        # Calculate enhanced priorities
        for file_info in valid_files:
            file_info['priority'] = self.calculate_enhanced_priority(
                file_info, primary_language, detected_frameworks
            )
        
        # Sort by priority (highest first)
        valid_files.sort(key=lambda x: x['priority'], reverse=True)
        
        # Smart selection within size limits
        selected_files = self._smart_size_selection(valid_files)
        
        self.logger.debug(f"Selected {len(selected_files)} files from {len(files)} total")
        return selected_files
    
    def _basic_filter(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply basic filtering rules"""
        valid_files = []
        
        for file_info in files:
            path = file_info.get('path', '')
            size = file_info.get('size', 0)
            
            # Skip empty paths
            if not path:
                continue
            
            # Skip excluded directories
            path_parts = path.lower().split('/')
            if any(Config.is_excluded_directory(part) for part in path_parts):
                continue
            
            # Skip binary files
            if Config.is_binary_file(path):
                continue
            
            # Skip files that are too large
            if size > Config.MAX_FILE_SIZE_BYTES:
                self.logger.debug(f"Skipping large file: {path} ({size} bytes)")
                continue
            
            # Skip empty files
            if size == 0:
                continue
            
            valid_files.append(file_info)
        
        return valid_files
    
    def _smart_size_selection(self, sorted_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Smart selection of files within size limits"""
        selected_files = []
        total_size = 0
        priority_groups = self._group_by_priority(sorted_files)
        
        # Always include highest priority files
        for priority_level in sorted(priority_groups.keys(), reverse=True):
            files_in_group = priority_groups[priority_level]
            
            for file_info in files_in_group:
                file_size = file_info.get('size', 0)
                
                # Check if we can fit this file
                if total_size + file_size <= Config.MAX_TOTAL_SIZE_BYTES:
                    selected_files.append(file_info)
                    total_size += file_size
                elif priority_level >= 800:  # Force include very important files
                    # Try to make room by removing lower priority files
                    if self._make_room_for_file(selected_files, file_info, file_size):
                        selected_files.append(file_info)
                        total_size = sum(f.get('size', 0) for f in selected_files)
            
            # Check if we're getting close to the limit
            if total_size > Config.MAX_TOTAL_SIZE_BYTES * 0.9:
                break
        
        return selected_files
    
    def _group_by_priority(self, files: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Group files by priority ranges"""
        groups = defaultdict(list)
        
        for file_info in files:
            priority = file_info.get('priority', 100)
            
            # Create priority groups
            if priority >= 1000:
                group = 1000
            elif priority >= 800:
                group = 800
            elif priority >= 600:
                group = 600
            elif priority >= 400:
                group = 400
            elif priority >= 200:
                group = 200
            else:
                group = 100
            
            groups[group].append(file_info)
        
        return groups
    
    def _make_room_for_file(self, selected_files: List[Dict[str, Any]], 
                           new_file: Dict[str, Any], new_file_size: int) -> bool:
        """Try to make room for a high-priority file by removing lower priority ones"""
        new_priority = new_file.get('priority', 0)
        
        # Find files with lower priority that we can remove
        removable_files = []
        for i, file_info in enumerate(selected_files):
            if file_info.get('priority', 0) < new_priority:
                removable_files.append((i, file_info))
        
        # Sort by priority (lowest first) and try to remove enough files
        removable_files.sort(key=lambda x: x[1].get('priority', 0))
        
        space_needed = new_file_size
        current_total = sum(f.get('size', 0) for f in selected_files)
        available_space = Config.MAX_TOTAL_SIZE_BYTES - current_total
        
        if available_space >= space_needed:
            return True  # No need to remove anything
        
        space_to_free = space_needed - available_space
        freed_space = 0
        files_to_remove = []
        
        for idx, file_info in removable_files:
            file_size = file_info.get('size', 0)
            files_to_remove.append(idx)
            freed_space += file_size
            
            if freed_space >= space_to_free:
                break
        
        if freed_space >= space_to_free:
            # Remove files in reverse order to maintain indices
            for idx in sorted(files_to_remove, reverse=True):
                del selected_files[idx]
            return True
        
        return False


class FileProcessor:
    """Main file processing class"""
    
    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self.logger = logger or AnalyzerLogger()
        self.prioritizer = FilePrioritizer(logger)
        self.language_detector = LanguageDetector()
        self.dependency_extractor = DependencyExtractor()
    
    def process_files(self, files: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process and filter files with priority scoring"""
        
        # Ensure input is a proper list
        if not isinstance(files, list):
            self.logger.warning(f"Expected list of files, got {type(files)}. Converting to empty list.")
            files = []
        
        # Filter out non-dictionary items
        valid_files = []
        for i, file_item in enumerate(files):
            if isinstance(file_item, dict):
                valid_files.append(file_item)
            else:
                self.logger.debug(f"Skipping non-dict file item at index {i}: {type(file_item)}")
        
        if len(valid_files) != len(files):
            self.logger.warning(f"Filtered out {len(files) - len(valid_files)} invalid file items")
        
        files = valid_files
        
        self.logger.debug("Starting file filtering and prioritization...")
        
        # Skip processing if no files
        if not files:
            self.logger.warning("No valid files to process")
            empty_metadata = {
                'languages': {},
                'primary_language': 'unknown',
                'frameworks': [],
                'dependencies': [],
                'total_files_processed': 0,
                'total_files_original': 0,
                'total_size_processed': 0,
                'total_size_original': 0,
                'size_reduction_ratio': 0,
                'file_type_stats': {},
                'priority_stats': {},
                'entry_points': [],
                'processing_timestamp': time.time()
            }
            return [], empty_metadata
        
        # Step 1: Basic filtering and validation
        filtered_files = self._filter_files(files)
        
        # Step 2: Priority scoring
        prioritized_files = self._assign_priorities(filtered_files)
        
        # Step 3: Size-based selection
        selected_files = self._select_by_size(prioritized_files)
        
        # Step 4: Content cleaning and validation
        processed_files = self._clean_and_validate_content(selected_files)
        
        # Step 5: Generate processing metadata
        processing_metadata = self._generate_processing_metadata(processed_files, files)
        
        self.logger.debug(f"Selected {len(processed_files)} files from {len(files)} total")
        
        return processed_files, processing_metadata
    
    def _clean_file_contents(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and validate file contents"""
        cleaned_files = []
        
        for file_info in files:
            try:
                content = file_info.get('content', '')
                if not content:
                    continue
                
                # Clean content for JSON safety
                cleaned_content = TextUtils.clean_json_string(content)
                
                # Validate content size after cleaning
                if len(cleaned_content.encode('utf-8')) > Config.MAX_FILE_SIZE_BYTES:
                    self.logger.debug(f"Content too large after cleaning: {file_info['path']}")
                    continue
                
                # Create cleaned file info
                cleaned_file = {
                    'path': ValidationUtils.sanitize_path(file_info['path']),
                    'content': cleaned_content,
                    'size': len(cleaned_content.encode('utf-8')),
                    'priority': file_info.get('priority', 100),
                    'hash': hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()[:16]
                }
                
                cleaned_files.append(cleaned_file)
            
            except Exception as e:
                self.logger.debug(f"Error cleaning file {file_info.get('path', 'unknown')}: {e}")
                continue
        
        return cleaned_files
    
    def _generate_processing_metadata(self, processed_files: List[Dict[str, Any]], 
                                original_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate metadata about the processing"""
        
        # Ensure inputs are lists
        if not isinstance(processed_files, list):
            processed_files = []
        if not isinstance(original_files, list):
            original_files = []
        
        # Language detection
        languages = self.language_detector.detect_languages(processed_files)
        primary_language = self.language_detector.detect_primary_language(processed_files)
        
        # Framework detection
        frameworks = self.language_detector.detect_frameworks(processed_files, primary_language)
        
        # Dependency extraction
        dependencies = self.dependency_extractor.extract_dependencies(processed_files, primary_language)
        
        # Size calculations - safe access with .get()
        total_processed_size = sum(f.get('size', 0) if isinstance(f, dict) else 0 for f in processed_files)
        total_original_size = sum(f.get('size', 0) if isinstance(f, dict) else 0 for f in original_files)
        
        # File statistics
        file_type_stats = self._calculate_file_type_stats(processed_files)
        priority_stats = self._calculate_priority_stats(processed_files)
        
        # Identify entry points
        entry_points = self._identify_entry_points(processed_files, primary_language)
        
        return {
            'languages': languages,
            'primary_language': primary_language,
            'frameworks': frameworks,
            'dependencies': dependencies,
            'total_files_processed': len(processed_files),
            'total_files_original': len(original_files),
            'total_size_processed': total_processed_size,
            'total_size_original': total_original_size,
            'size_reduction_ratio': (1 - total_processed_size / total_original_size) if total_original_size > 0 else 0,
            'file_type_stats': file_type_stats,
            'priority_stats': priority_stats,
            'entry_points': entry_points,
            'processing_timestamp': time.time()
        }
    
    def _calculate_file_type_stats(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate statistics by file type"""
        stats = defaultdict(int)
        
        for file_info in files:
            path = file_info.get('path', '')
            ext = Path(path).suffix.lower()
            
            if ext:
                stats[ext] += 1
            else:
                stats['no_extension'] += 1
        
        # Sort by count and return top 20
        sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
        return dict(list(sorted_stats.items())[:20])
    
    def _calculate_priority_stats(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate statistics by priority ranges"""
        stats = {
            'very_high_1000+': 0,
            'high_800-999': 0,
            'medium_600-799': 0,
            'normal_400-599': 0,
            'low_200-399': 0,
            'very_low_0-199': 0
        }
        
        for file_info in files:
            priority = file_info.get('priority', 100)
            
            if priority >= 1000:
                stats['very_high_1000+'] += 1
            elif priority >= 800:
                stats['high_800-999'] += 1
            elif priority >= 600:
                stats['medium_600-799'] += 1
            elif priority >= 400:
                stats['normal_400-599'] += 1
            elif priority >= 200:
                stats['low_200-399'] += 1
            else:
                stats['very_low_0-199'] += 1
        
        return stats
    
    def _identify_entry_points(self, files: List[Dict[str, Any]], primary_language: str) -> List[str]:
        """Identify likely entry point files"""
        entry_points = []
        
        if primary_language in Config.LANGUAGE_PRIORITY_PATTERNS:
            entry_point_patterns = Config.LANGUAGE_PRIORITY_PATTERNS[primary_language].get('entry_points', [])
            
            for file_info in files:
                path = file_info.get('path', '')
                filename = Path(path).name
                
                if filename in entry_point_patterns:
                    entry_points.append(path)
        
        # Also look for files with very high priority
        high_priority_files = [
            f['path'] for f in files 
            if f.get('priority', 0) >= 1000
        ]
        
        # Combine and deduplicate
        all_entry_points = list(set(entry_points + high_priority_files))
        
        # Sort by priority and return top 10
        file_priority_map = {f['path']: f.get('priority', 0) for f in files}
        all_entry_points.sort(key=lambda x: file_priority_map.get(x, 0), reverse=True)
        
        return all_entry_points[:10]
    
    def _fallback_processing(self, raw_files: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fallback processing for memory-constrained situations"""
        self.logger.warning("Using fallback processing due to memory constraints")
        
        # Only process highest priority files
        basic_filtered = self.prioritizer._basic_filter(raw_files)
        
        # Calculate basic priorities
        for file_info in basic_filtered:
            file_info['priority'] = Config.get_file_priority(file_info['path'])
        
        # Sort and take top files
        basic_filtered.sort(key=lambda x: x['priority'], reverse=True)
        
        # Select files within a smaller size limit (50% of max)
        selected_files = []
        total_size = 0
        size_limit = Config.MAX_TOTAL_SIZE_BYTES // 2
        
        for file_info in basic_filtered:
            file_size = file_info.get('size', 0)
            if total_size + file_size <= size_limit:
                selected_files.append(file_info)
                total_size += file_size
            
            if len(selected_files) >= 50:  # Limit file count too
                break
        
        # Basic metadata
        metadata = {
            'languages': {'unknown': 100.0},
            'primary_language': 'unknown',
            'frameworks': [],
            'dependencies': [],
            'total_files_processed': len(selected_files),
            'total_files_original': len(raw_files),
            'total_size_processed': total_size,
            'fallback_mode': True
        }
        
        return selected_files, metadata

    def get_processing_summary(self, processed_files: List[Dict[str, Any]], 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of processing results"""
        return {
            'total_files': len(processed_files),
            'total_size_mb': metadata.get('total_size_processed', 0) / (1024 * 1024),
            'primary_language': metadata.get('primary_language', 'unknown'),
            'frameworks_detected': len(metadata.get('frameworks', [])),
            'dependencies_found': len(metadata.get('dependencies', [])),
            'entry_points': len(metadata.get('entry_points', [])),
            'size_reduction': f"{metadata.get('size_reduction_ratio', 0) * 100:.1f}%",
            'processing_mode': 'fallback' if metadata.get('fallback_mode') else 'full'
        }
    
    def _filter_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter files based on inclusion/exclusion criteria"""
        filtered = []
        
        for file_info in files:
            path = file_info.get('path', '')
            size = file_info.get('size', 0)
            
            # Skip excluded directories
            if any(Config.is_excluded_directory(part) for part in path.split('/')):
                continue
            
            # Skip binary files
            if Config.is_binary_file(path):
                continue
            
            # Skip too large files
            if size > Config.MAX_FILE_SIZE_BYTES:
                continue
            
            # Skip empty files
            if size == 0:
                continue
            
            filtered.append(file_info)
        
        return filtered

    def _assign_priorities(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assign priority scores to files"""
        for file_info in files:
            path = file_info.get('path', '')
            file_info['priority'] = Config.get_file_priority(path)
        
        return files

    def _select_by_size(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select files based on size constraints"""
        # Sort by priority
        files.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        total_size = 0
        selected = []
        
        for file_info in files:
            file_size = file_info.get('size', 0)
            if total_size + file_size <= Config.MAX_TOTAL_SIZE_BYTES:
                selected.append(file_info)
                total_size += file_size
            else:
                break
        
        return selected

    def _clean_and_validate_content(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and validate file contents"""
        self.logger.debug("Cleaning and validating file contents...")
        
        cleaned = []
        for file_info in files:
            if 'content' not in file_info:
                # File without content, skip
                continue
            
            content = file_info['content']
            if isinstance(content, str) and len(content.strip()) > 0:
                # Clean content
                file_info['content'] = content.strip()
                cleaned.append(file_info)
        
        return cleaned
