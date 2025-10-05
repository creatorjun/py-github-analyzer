"""
Unit tests for MetadataGenerator
Comprehensive testing of metadata generation and analysis formatting
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from py_github_analyzer.metadata_generator import MetadataGenerator


@pytest.mark.unit
class TestMetadataGenerator:
    """Test MetadataGenerator main functionality"""

    @pytest.fixture
    def metadata_generator(self, mock_logger):
        """Create MetadataGenerator instance for testing"""
        return MetadataGenerator(logger=mock_logger)

    def test_metadata_generator_initialization(self, mock_logger):
        """Test MetadataGenerator initialization"""
        generator = MetadataGenerator(logger=mock_logger)
        assert generator.logger == mock_logger

    def test_generate_metadata_success(self, metadata_generator, sample_file_contents, sample_repository_info):
        """Test successful metadata generation"""
        processing_metadata = {
            'total_files': len(sample_file_contents),
            'total_size': sum(f['size'] for f in sample_file_contents),
            'languages': {'Python': 80, 'Markdown': 20},
            'frameworks': ['pytest'],
            'dependencies': ['requests', 'pytest', 'httpx'],
            'primary_language': 'Python'
        }

        result = metadata_generator.generate_metadata(
            sample_file_contents,
            sample_repository_info,
            processing_metadata
        )

        # Verify required top-level keys
        required_keys = [
            'summary', 'repository', 'analysis', 'files',
            'languages', 'dependencies', 'frameworks', 'structure'
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Verify summary content
        assert isinstance(result['summary'], str)
        assert len(result['summary']) > 50  # Should be a meaningful summary

        # Verify repository information
        assert result['repository']['name'] == 'test-repo'
        assert result['repository']['language'] == 'Python'

        # Verify analysis results
        assert result['analysis']['total_files'] == len(sample_file_contents)
        assert result['analysis']['total_size'] > 0
        assert 'Python' in result['languages']

    def test_generate_metadata_empty_files(self, metadata_generator, sample_repository_info):
        """Test metadata generation with empty files"""
        processing_metadata = {
            'total_files': 0,
            'total_size': 0,
            'languages': {},
            'frameworks': [],
            'dependencies': [],
            'primary_language': 'Unknown'
        }

        result = metadata_generator.generate_metadata([], sample_repository_info, processing_metadata)
        assert result['analysis']['total_files'] == 0
        assert result['analysis']['total_size'] == 0
        assert result['languages'] == {}
        assert result['dependencies'] == []
        assert result['frameworks'] == []

    def test_generate_summary_comprehensive(self, metadata_generator, sample_file_contents, sample_repository_info):
        """Test comprehensive summary generation"""
        processing_metadata = {
            'total_files': len(sample_file_contents),
            'total_size': 1024,
            'languages': {'Python': 70, 'JavaScript': 20, 'Markdown': 10},
            'frameworks': ['django', 'react'],
            'dependencies': ['requests', 'express', 'pytest'],
            'primary_language': 'Python'
        }

        summary = metadata_generator.generate_summary(
            sample_repository_info,
            sample_file_contents,
            processing_metadata
        )

        # Verify summary contains key information
        assert 'test-repo' in summary
        assert 'Python' in summary
        assert str(len(sample_file_contents)) in summary
        assert 'django' in summary or 'react' in summary

        # Verify summary structure
        assert len(summary) > 100  # Should be substantial
        assert summary.count('.') >= 3  # Should have multiple sentences

    def test_generate_summary_minimal_repo(self, metadata_generator):
        """Test summary generation for minimal repository"""
        minimal_repo_info = {
            'name': 'minimal-repo',
            'description': '',
            'language': None,
            'topics': []
        }

        minimal_files = [
            {'path': 'README.md', 'content': '# Minimal', 'size': 10}
        ]

        minimal_metadata = {
            'total_files': 1,
            'total_size': 10,
            'languages': {'Markdown': 100},
            'frameworks': [],
            'dependencies': [],
            'primary_language': 'Markdown'
        }

        summary = metadata_generator.generate_summary(
            minimal_repo_info,
            minimal_files,
            minimal_metadata
        )

        assert 'minimal-repo' in summary
        assert len(summary) > 20  # Should still generate meaningful content

    def test_create_structure_analysis(self, metadata_generator, sample_file_contents):
        """Test repository structure analysis"""
        files_with_paths = [
            {'path': 'src/main.py', 'size': 100},
            {'path': 'src/utils.py', 'size': 50},
            {'path': 'tests/test_main.py', 'size': 80},
            {'path': 'tests/conftest.py', 'size': 30},
            {'path': 'docs/README.md', 'size': 200},
            {'path': 'docs/api.md', 'size': 150},
            {'path': 'requirements.txt', 'size': 40},
            {'path': '.gitignore', 'size': 20}
        ]

        structure = metadata_generator.create_structure_analysis(files_with_paths)

        # Verify directory structure
        assert 'src' in structure
        assert 'tests' in structure
        assert 'docs' in structure
        assert structure['src'] == 2  # 2 files in src/
        assert structure['tests'] == 2  # 2 files in tests/
        assert structure['docs'] == 2  # 2 files in docs/

    def test_create_structure_analysis_flat(self, metadata_generator):
        """Test structure analysis for flat repository"""
        flat_files = [
            {'path': 'main.py', 'size': 100},
            {'path': 'utils.py', 'size': 50},
            {'path': 'README.md', 'size': 200}
        ]

        structure = metadata_generator.create_structure_analysis(flat_files)
        # Should show root level files
        assert 'root' in structure or len(structure) == 0

    def test_calculate_complexity_metrics(self, metadata_generator, sample_file_contents):
        """Test complexity metrics calculation"""
        # Add some mock complexity data to files
        files_with_complexity = []
        for file_info in sample_file_contents:
            file_copy = file_info.copy()
            if file_info['path'].endswith('.py'):
                file_copy['complexity'] = 5.5
                file_copy['lines'] = 100
            else:
                file_copy['complexity'] = 1.0
                file_copy['lines'] = 20
            files_with_complexity.append(file_copy)

        metrics = metadata_generator.calculate_complexity_metrics(files_with_complexity)
        assert 'average_complexity' in metrics
        assert 'max_complexity' in metrics
        assert 'total_lines' in metrics
        assert metrics['average_complexity'] > 0
        assert metrics['total_lines'] > 0

    def test_extract_key_features(self, metadata_generator, sample_repository_info):
        """Test key feature extraction"""
        processing_metadata = {
            'frameworks': ['django', 'react', 'pytest'],
            'dependencies': ['requests', 'numpy', 'express'],
            'languages': {'Python': 60, 'JavaScript': 30, 'CSS': 10}
        }

        features = metadata_generator.extract_key_features(
            sample_repository_info,
            processing_metadata
        )

        assert 'web_development' in features or 'backend' in features
        assert 'testing' in features  # pytest should indicate testing
        assert 'python' in features  # Primary language

    def test_extract_dependencies_comprehensive(self, metadata_generator):
        """Test comprehensive dependency extraction"""
        files_with_deps = [
            {
                'path': 'requirements.txt',
                'content': 'requests>=2.28.0\nflask==2.3.2\nnumpy>=1.24.0',
                'dependencies': ['requests', 'flask', 'numpy']
            },
            {
                'path': 'package.json',
                'content': '{"dependencies": {"express": "^4.18.0"}}',
                'dependencies': ['express', 'lodash']
            },
            {
                'path': 'main.py',
                'content': 'import os\nimport requests\nfrom flask import Flask',
                'imports': ['os', 'requests', 'flask']
            }
        ]

        processing_metadata = {
            'dependencies': ['requests', 'flask', 'express']
        }

        dependencies = metadata_generator.extract_dependencies(files_with_deps, processing_metadata)
        assert 'requests' in dependencies
        assert 'flask' in dependencies
        assert 'express' in dependencies
        assert len(dependencies) <= 20  # Should limit to top 20

    def test_extract_dependencies_from_file_content(self, metadata_generator):
        """Test dependency extraction from specific file content"""
        # Test requirements.txt
        requirements_content = """requests>=2.28.0
flask==2.3.2
# Development dependencies
pytest>=7.0.0
black"""
        deps = metadata_generator.extract_dependencies_from_file(requirements_content, 'requirements.txt')
        assert 'requests' in deps
        assert 'flask' in deps
        assert 'pytest' in deps
        assert 'black' in deps

        # Test package.json
        package_json_content = """{
    "dependencies": {
        "express": "^4.18.0",
        "lodash": "^4.17.21"
    },
    "devDependencies": {
        "jest": "^29.0.0"
    }
}"""
        deps = metadata_generator.extract_dependencies_from_file(package_json_content, 'package.json')
        assert 'express' in deps
        assert 'lodash' in deps
        assert 'jest' in deps

    def test_safe_size_calculation(self, metadata_generator):
        """Test safe size calculation utility"""
        # Test various input types
        assert metadata_generator.safe_size_calculation(1024) == 1024
        assert metadata_generator.safe_size_calculation("1024") == 1024
        assert metadata_generator.safe_size_calculation("1024.5") == 1024
        assert metadata_generator.safe_size_calculation("invalid") == 0
        assert metadata_generator.safe_size_calculation(None) == 0
        assert metadata_generator.safe_size_calculation([]) == 0

    def test_safe_percentage_calculation(self, metadata_generator):
        """Test safe percentage calculation utility"""
        # Test normal cases
        assert metadata_generator.safe_percentage_calculation(25, 100) == 25.0
        assert abs(metadata_generator.safe_percentage_calculation(1, 3) - 33.33) < 0.01

        # Test edge cases
        assert metadata_generator.safe_percentage_calculation(10, 0) == 0.0
        assert metadata_generator.safe_percentage_calculation(0, 100) == 0.0
        assert metadata_generator.safe_percentage_calculation("invalid", 100) == 0.0

    def test_format_size(self):
        """Test size formatting utility - 모듈 수준 함수 테스트"""
        from py_github_analyzer.metadata_generator import format_size

        assert format_size(512) == "512B"
        assert format_size(1024) == "1.0KB"
        assert format_size(1048576) == "1.0MB"
        assert format_size(1073741824) == "1.0GB"

        # Edge cases
        assert format_size(0) == "0B"
        assert format_size(-1) == "0B"  # Negative values should return 0B

    def test_generate_metadata_with_error_handling(self, metadata_generator, sample_repository_info, mock_logger):
        """Test metadata generation with error handling"""
        # Create problematic data that might cause errors
        problematic_files = [
            {'path': 'test.py', 'content': None, 'size': 'invalid'},  # Invalid size
            {'path': None, 'content': 'test', 'size': 100}  # Invalid path
        ]

        problematic_metadata = {
            'total_files': 'invalid',  # Invalid type
            'languages': None,  # Invalid type
            'frameworks': 'not_a_list',  # Invalid type
            'dependencies': None  # Invalid type
        }

        # Should handle errors gracefully and return valid metadata
        result = metadata_generator.generate_metadata(
            problematic_files,
            sample_repository_info,
            problematic_metadata
        )

        # Should still return valid structure
        assert 'summary' in result
        assert 'repository' in result
        assert 'analysis' in result

        # Should log errors
        mock_logger.debug.assert_called()


@pytest.mark.integration
class TestMetadataGeneratorIntegration:
    """Integration tests for MetadataGenerator"""

    @pytest.fixture
    def metadata_generator(self, mock_logger):
        """Create MetadataGenerator instance for testing"""
        return MetadataGenerator(logger=mock_logger)

    def test_complete_metadata_generation_pipeline(self, metadata_generator, sample_file_contents, sample_repository_info):
        """Test complete metadata generation pipeline"""
        # Create comprehensive processing metadata
        processing_metadata = {
            'total_files': len(sample_file_contents),
            'total_size': sum(f['size'] for f in sample_file_contents),
            'languages': {
                'Python': 70,
                'JavaScript': 20,
                'Markdown': 8,
                'JSON': 2
            },
            'file_types': {
                '.py': 3,
                '.js': 1,
                '.md': 1,
                '.json': 1
            },
            'frameworks': ['django', 'react', 'pytest'],
            'dependencies': [
                'requests', 'flask', 'numpy', 'pandas',
                'express', 'lodash', 'react', 'axios',
                'pytest', 'jest', 'eslint'
            ],
            'primary_language': 'Python',
            'complexity_stats': {
                'average_complexity': 3.5,
                'max_complexity': 8.2,
                'total_lines': 1250
            },
            'structure_analysis': {
                'src': 5,
                'tests': 3,
                'docs': 2,
                'config': 1
            }
        }

        result = metadata_generator.generate_metadata(
            sample_file_contents,
            sample_repository_info,
            processing_metadata
        )

        # Verify comprehensive structure
        assert isinstance(result, dict)

        # Verify summary quality
        summary = result['summary']
        assert len(summary) > 200  # Should be comprehensive
        assert 'test-repo' in summary
        assert 'Python' in summary

        # Verify repository information preservation
        repo_info = result['repository']
        assert repo_info['name'] == sample_repository_info['name']
        assert repo_info['language'] == sample_repository_info['language']

        # Verify analysis completeness
        analysis = result['analysis']
        assert analysis['total_files'] == len(sample_file_contents)
        assert analysis['primary_language'] == 'Python'
        assert 'complexity_metrics' in analysis

        # Verify files information
        assert len(result['files']) == len(sample_file_contents)

        # Verify language distribution
        assert 'Python' in result['languages']
        assert result['languages']['Python'] == 70

        # Verify dependencies and frameworks
        assert len(result['dependencies']) > 0
        assert 'django' in result['frameworks']
        assert 'react' in result['frameworks']

        # Verify structure analysis
        assert 'src' in result['structure']
        assert result['structure']['src'] == 5

    def test_metadata_json_serialization(self, metadata_generator, sample_file_contents, sample_repository_info):
        """Test that generated metadata is JSON serializable"""
        processing_metadata = {
            'total_files': len(sample_file_contents),
            'total_size': 1024,
            'languages': {'Python': 100},
            'frameworks': ['flask'],
            'dependencies': ['requests'],
            'primary_language': 'Python'
        }

        result = metadata_generator.generate_metadata(
            sample_file_contents,
            sample_repository_info,
            processing_metadata
        )

        # Should be able to serialize to JSON without errors
        json_string = json.dumps(result, indent=2)
        assert len(json_string) > 100

        # Should be able to deserialize back
        deserialized = json.loads(json_string)
        assert deserialized['repository']['name'] == 'test-repo'

    def test_large_repository_handling(self, metadata_generator, sample_repository_info):
        """Test metadata generation for large repositories"""
        # Simulate large repository with many files
        large_file_list = []
        for i in range(1000):  # 1000 files
            large_file_list.append({
                'path': f'src/module_{i}.py',
                'content': f'# Module {i}\nprint("Module {i}")',
                'size': 50 + (i % 100)
            })

        processing_metadata = {
            'total_files': 1000,
            'total_size': 75000,  # ~75KB total
            'languages': {'Python': 100},
            'frameworks': ['django', 'pytest'],
            'dependencies': ['requests', 'numpy', 'pandas'] * 10,  # Many dependencies
            'primary_language': 'Python'
        }

        result = metadata_generator.generate_metadata(
            large_file_list,
            sample_repository_info,
            processing_metadata
        )

        # Should handle large repositories efficiently
        assert result['analysis']['total_files'] == 1000
        assert len(result['dependencies']) <= 20  # Should limit dependencies
        assert len(result['files']) == 1000  # Should include all files

        # Summary should still be reasonable length
        assert len(result['summary']) < 2000  # Should not be excessively long

    def test_multilingual_repository_handling(self, metadata_generator, sample_repository_info):
        """Test metadata generation for multilingual repositories"""
        multilingual_files = [
            {'path': 'backend/app.py', 'content': 'from flask import Flask', 'size': 100},
            {'path': 'backend/models.py', 'content': 'from sqlalchemy import Column', 'size': 150},
            {'path': 'frontend/app.js', 'content': 'import React from "react"', 'size': 80},
            {'path': 'frontend/components/Header.jsx', 'content': 'export default function Header()', 'size': 120},
            {'path': 'mobile/MainActivity.java', 'content': 'public class MainActivity', 'size': 200},
            {'path': 'mobile/UserService.kt', 'content': 'class UserService {', 'size': 90},
            {'path': 'scripts/build.sh', 'content': '#!/bin/bash\necho "Building..."', 'size': 50},
            {'path': 'config/nginx.conf', 'content': 'server { listen 80; }', 'size': 40}
        ]

        processing_metadata = {
            'total_files': len(multilingual_files),
            'total_size': sum(f['size'] for f in multilingual_files),
            'languages': {
                'Python': 30,
                'JavaScript': 25,
                'Java': 20,
                'Kotlin': 15,
                'Shell': 6,
                'Nginx': 4
            },
            'frameworks': ['flask', 'react', 'android'],
            'dependencies': ['flask', 'react', 'axios', 'retrofit'],
            'primary_language': 'Python'
        }

        result = metadata_generator.generate_metadata(
            multilingual_files,
            sample_repository_info,
            processing_metadata
        )

        # Should handle multiple languages properly
        assert len(result['languages']) >= 4  # Should detect multiple languages
        assert 'Python' in result['languages']
        assert 'JavaScript' in result['languages']
        assert 'Java' in result['languages']

        # Summary should mention the multilingual nature
        summary = result['summary']
        assert 'multilingual' in summary.lower() or len(result['languages']) > 1

        # Should detect frameworks from different ecosystems
        frameworks = result['frameworks']
        assert 'flask' in frameworks
        assert 'react' in frameworks

    def test_performance_with_large_content(self, metadata_generator, sample_repository_info):
        """Test performance with large file content"""
        # Create files with large content
        large_content_files = []
        for i in range(10):
            large_content = "# Large file content\n" * 1000  # 20KB+ per file
            large_content_files.append({
                'path': f'large_file_{i}.py',
                'content': large_content,
                'size': len(large_content)
            })

        processing_metadata = {
            'total_files': 10,
            'total_size': sum(f['size'] for f in large_content_files),
            'languages': {'Python': 100},
            'frameworks': ['django'],
            'dependencies': ['requests', 'flask'],
            'primary_language': 'Python'
        }

        # Should complete without performance issues
        result = metadata_generator.generate_metadata(
            large_content_files,
            sample_repository_info,
            processing_metadata
        )

        assert result['analysis']['total_files'] == 10
        assert result['analysis']['total_size'] > 200000  # Should be substantial

    def test_special_characters_handling(self, metadata_generator, sample_repository_info):
        """Test handling of files with special characters and Unicode"""
        special_files = [
            {'path': 'файл.py', 'content': '# Русский комментарий\nprint("Привет")', 'size': 50},
            {'path': '文件.js', 'content': '// 中文注释\nconsole.log("你好");', 'size': 60},
            {'path': 'émoji_😀.md', 'content': '# Émoji in filename 😀\nSpecial chars: àáâãäå', 'size': 70}
        ]

        processing_metadata = {
            'total_files': 3,
            'total_size': 180,
            'languages': {'Python': 40, 'JavaScript': 35, 'Markdown': 25},
            'frameworks': [],
            'dependencies': [],
            'primary_language': 'Python'
        }

        result = metadata_generator.generate_metadata(
            special_files,
            sample_repository_info,
            processing_metadata
        )

        # Should handle Unicode properly
        assert result['analysis']['total_files'] == 3
        assert len(result['files']) == 3

        # Should be JSON serializable despite Unicode
        json_string = json.dumps(result, ensure_ascii=False, indent=2)
        assert len(json_string) > 100
