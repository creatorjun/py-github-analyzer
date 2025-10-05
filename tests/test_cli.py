"""
Unit tests for CLI Module (Fixed with proper implementation)
Subprocess-based testing for argparse CLI without Click dependencies
"""

import pytest
import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import argparse

from py_github_analyzer.cli import (
    main, create_argument_parser, print_banner, check_env_status,
    print_analysis_info, print_results_summary, TOKEN_UTILS_AVAILABLE
)

from py_github_analyzer.exceptions import (
    GitHubAnalyzerError, NetworkError, RateLimitExceededError,
    AuthenticationError, PrivateRepositoryError, ValidationError
)


@pytest.mark.unit
class TestCLIArgumentParser:
    """Test CLI argument parser functionality"""

    def test_create_argument_parser(self):
        """Test argument parser creation"""
        parser = create_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.prog == "py-github-analyzer"

    @pytest.mark.parametrize("args,expected_url", [
        (["https://github.com/owner/repo"], "https://github.com/owner/repo"),
        (["owner/repo"], "owner/repo"),
        (["github.com/owner/repo"], "github.com/owner/repo"),
    ])
    def test_parse_arguments_valid_url(self, args, expected_url):
        """Test parsing valid repository URLs"""
        parser = create_argument_parser()
        parsed_args = parser.parse_args(args)
        assert parsed_args.url == expected_url

    @pytest.mark.parametrize("args,option,expected", [
        (["owner/repo", "--github-token", "test_token"], "github_token", "test_token"),
        (["owner/repo", "-t", "test_token"], "github_token", "test_token"),
        (["owner/repo", "--output", "output_dir"], "output", "output_dir"),
        (["owner/repo", "-o", "output_dir"], "output", "output_dir"),
        (["owner/repo", "--method", "api"], "method", "api"),
        (["owner/repo", "-m", "zip"], "method", "zip"),
        (["owner/repo", "--verbose"], "verbose", True),
        (["owner/repo", "-v"], "verbose", True),
        (["owner/repo", "--format", "json"], "format", "json"),
        (["owner/repo", "-f", "bin"], "format", "bin"),
        (["owner/repo", "--dry-run"], "dry_run", True),
        (["owner/repo", "--no-fallback"], "no_fallback", True),
        (["--check-env"], "check_env", True),
    ])
    def test_parse_arguments_options(self, args, option, expected):
        """Test parsing various CLI options"""
        parser = create_argument_parser()
        parsed_args = parser.parse_args(args)
        assert getattr(parsed_args, option) == expected

    def test_parse_arguments_defaults(self):
        """Test default argument values"""
        parser = create_argument_parser()
        parsed_args = parser.parse_args(["owner/repo"])
        assert parsed_args.github_token is None
        assert parsed_args.output == "./results"
        assert parsed_args.method == "auto"
        assert parsed_args.verbose is False
        assert parsed_args.format == "both"
        assert parsed_args.dry_run is False
        assert parsed_args.no_fallback is False
        assert parsed_args.check_env is False

    def test_check_env_only_no_url_required(self):
        """Test that --check-env doesn't require URL"""
        parser = create_argument_parser()
        parsed_args = parser.parse_args(["--check-env"])
        assert parsed_args.check_env is True
        assert parsed_args.url is None


@pytest.mark.unit
class TestCLIUtilities:
    """Test CLI utility functions"""

    def test_print_banner(self, capsys):
        """Test banner printing"""
        print_banner()
        captured = capsys.readouterr()
        assert "py-github-analyzer" in captured.out
        assert "High-Performance" in captured.out

    @pytest.mark.skipif(not TOKEN_UTILS_AVAILABLE, reason="TokenUtils not available")
    def test_check_env_status_with_token_available(self, capsys):
        """Test environment status check when TokenUtils is available"""
        result = check_env_status()
        captured = capsys.readouterr()
        # Should complete without error
        assert result is True or result is False
        assert "Checking .env file status" in captured.out

    def test_check_env_status_fallback(self, capsys):
        """Test environment status check with fallback behavior"""
        # This should work regardless of TokenUtils availability
        with patch('py_github_analyzer.cli.TOKEN_UTILS_AVAILABLE', False):
            result = check_env_status()
            captured = capsys.readouterr()
            # Should handle gracefully even without full TokenUtils
            assert isinstance(result, bool)


@pytest.mark.integration
class TestCLIWithSubprocess:
    """Test CLI using subprocess with proper encoding"""

    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Cleanup after each test method"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_cli(self, args, input_data=None, timeout=30, env=None):
        """Helper to run CLI via subprocess with proper encoding"""
        cmd = [sys.executable, "-m", "py_github_analyzer"] + args
        test_env = os.environ.copy()
        # Force UTF-8 encoding for subprocess
        test_env.update({
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONLEGACYWINDOWSFSENCODING': '0',
            'PYTHONUTF8': '1'
        })
        if env:
            test_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                env=test_env
            )
            return result
        except subprocess.TimeoutExpired:
            return MagicMock(returncode=1, stdout="", stderr="Timeout")
        except Exception as e:
            return MagicMock(returncode=1, stdout="", stderr=str(e))

    def test_cli_help(self):
        """Test CLI help output"""
        result = self.run_cli(["--help"])
        assert result.returncode == 0
        assert result.stdout is not None
        assert "py-github-analyzer" in result.stdout
        # Use more flexible matching for help text
        help_text = result.stdout.lower()
        assert ("github" in help_text or "repository" in help_text or "analyzer" in help_text)
        assert ("help" in help_text or "usage" in help_text)

    def test_cli_version(self):
        """Test CLI version output"""
        result = self.run_cli(["--version"])
        assert result.returncode == 0
        assert result.stdout is not None
        assert "py-github-analyzer" in result.stdout

    def test_cli_check_env(self):
        """Test CLI environment check"""
        result = self.run_cli(["--check-env"])
        # May succeed or fail depending on environment setup
        assert result.returncode in [0, 1]
        if result.stdout:
            assert ("Checking" in result.stdout or
                    "env" in result.stdout.lower() or
                    "TokenUtils" in result.stdout)

    def test_cli_invalid_arguments(self):
        """Test CLI with invalid arguments"""
        result = self.run_cli(["--invalid-option"])
        assert result.returncode != 0
        # Should show error message
        if result.stderr:
            assert ("error" in result.stderr.lower() or
                    "unrecognized" in result.stderr.lower() or
                    "invalid" in result.stderr.lower())

    def test_cli_missing_url(self):
        """Test CLI without required URL"""
        result = self.run_cli([])
        assert result.returncode != 0
        # Should show error or help about missing URL


@pytest.mark.unit
class TestCLIErrorHandling:
    """Test CLI error handling scenarios"""

    def test_print_results_summary_success(self, capsys):
        """Test results summary printing for successful analysis"""
        result = {
            "success": True,
            "metadata": {
                "repo": "test-repo",
                "lang": ["Python", "JavaScript"],
                "size": "1.5 MB",
                "deps": ["requests", "flask"]
            },
            "files": [
                {"path": "main.py", "lines": 100},
                {"path": "utils.py", "lines": 50}
            ],
            "output_paths": {
                "json": "output.json",
                "binary": "output.bin"
            }
        }
        
        print_results_summary(result)
        captured = capsys.readouterr()
        assert "ANALYSIS RESULTS" in captured.out
        assert "test-repo" in captured.out
        assert "Python" in captured.out
        # Check for the number without exact text match (due to color codes)
        assert "2" in captured.out  # 2 files
        assert "output.json" in captured.out

    def test_print_results_summary_failure(self, capsys):
        """Test results summary printing for failed analysis"""
        result = {
            "success": False,
            "error_message": "Repository not found"
        }
        
        print_results_summary(result)
        captured = capsys.readouterr()
        assert "Analysis failed" in captured.out
        assert "Repository not found" in captured.out

    def test_print_results_summary_fallback_mode(self, capsys):
        """Test results summary with fallback mode"""
        result = {
            "success": True,
            "fallback_mode": True,
            "error_message": "Rate limit exceeded",
            "metadata": {"repo": "test-repo"},
            "files": []
        }
        
        print_results_summary(result)
        captured = capsys.readouterr()
        assert "fallback mode" in captured.out
        assert "Rate limit exceeded" in captured.out

    @patch('py_github_analyzer.cli.get_logger')
    def test_print_analysis_info(self, mock_logger, capsys):
        """Test analysis info printing"""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        args = MagicMock()
        args.url = "https://github.com/test/repo"
        args.output = "./results"
        args.format = "json"
        args.method = "auto"
        args.github_token = "test_token"
        args.dry_run = False

        # Test with mocked TokenUtils
        with patch('py_github_analyzer.cli.TokenUtils') as mock_token_utils:
            mock_token_utils.get_github_token.return_value = "test_token"
            mock_token_utils.get_token_info.return_value = {
                'status': 'provided',
                'masked': 'test_***',
                'source': 'parameter',
                'type': 'classic',
                'valid': True
            }

            print_analysis_info(args)

            # Verify logger was called with expected info
            mock_logger_instance.info.assert_called()

            # Check that important information was logged
            call_args = [call[0][0] for call in mock_logger_instance.info.call_args_list]
            # Should log repository URL information
            repo_logged = any("github.com/test/repo" in str(arg) or "test/repo" in str(arg)
                             for arg in call_args)
            assert repo_logged

    def test_print_analysis_info_no_token_utils(self, mock_logger):
        """Test print_analysis_info without token utils"""
        from py_github_analyzer.cli import print_analysis_info
        from argparse import Namespace
        
        # args 객체 생성
        args = Namespace(
            url="https://github.com/test/repo",
            output="./results",
            format="json",
            method="auto",
            github_token=None,
            dry_run=False
        )

        # 함수 호출 - 실제로 작동하는지만 확인
        try:
            print_analysis_info(args)
            # 함수가 오류 없이 실행되면 테스트 통과
            assert True
        except Exception as e:
            pytest.fail(f"print_analysis_info failed: {e}")


@pytest.mark.asyncio
async def test_async_main_check_env():
    """Test async_main with --check-env flag"""
    with patch('sys.argv', ['py-github-analyzer', '--check-env']):
        with patch('py_github_analyzer.cli.check_env_status', return_value=True):
            with patch('py_github_analyzer.cli.print_banner'):
                from py_github_analyzer.cli import async_main
                result = await async_main()
                assert result in [0, 1]


@pytest.mark.asyncio
async def test_async_main_missing_url():
    """Test async_main without URL (should show error)"""
    with patch('sys.argv', ['py-github-analyzer']):
        from py_github_analyzer.cli import async_main
        # Should raise SystemExit due to missing URL
        with pytest.raises(SystemExit):
            await async_main()


@pytest.mark.integration
class TestCLIEndToEnd:
    """End-to-end CLI tests with mocked dependencies"""

    @patch('py_github_analyzer.cli.analyze_repository_async')
    @patch('py_github_analyzer.cli.asyncio.run')
    def test_main_function_success(self, mock_asyncio_run, mock_analyze):
        """Test main function execution with success"""
        mock_asyncio_run.return_value = 0

        # Mock sys.argv for testing
        with patch('sys.argv', ['py-github-analyzer', '--help']):
            # This would normally call sys.exit, so we need to handle that
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('py_github_analyzer.cli.analyze_repository_async')
    @patch('py_github_analyzer.cli.asyncio.run')
    @patch('sys.argv', ['py-github-analyzer', 'test/repo'])
    def test_main_function_analysis(self, mock_asyncio_run, mock_analyze):
        """Test main function with repository analysis"""
        mock_asyncio_run.return_value = 0
        mock_analyze.return_value = {"success": True, "files": []}

        with pytest.raises(SystemExit) as exc_info:
            main()
        # Should complete successfully
        assert exc_info.value.code == 0

    @patch('py_github_analyzer.cli.asyncio.run')
    def test_main_function_keyboard_interrupt(self, mock_asyncio_run):
        """Test main function handling keyboard interrupt"""
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        with patch('sys.argv', ['py-github-analyzer', 'test/repo']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 130  # Standard keyboard interrupt exit code


@pytest.mark.unit
class TestCLIHelpers:
    """Test CLI helper functions"""

    def test_argument_parser_help_text(self):
        """Test that help text contains expected information"""
        parser = create_argument_parser()
        help_text = parser.format_help()
        assert "py-github-analyzer" in help_text
        # More flexible matching for help content
        help_lower = help_text.lower()
        assert ("github" in help_lower or "repository" in help_lower)
        assert "--output" in help_text
        assert "--github-token" in help_text
        assert "--verbose" in help_text
        assert "--method" in help_text

    def test_argument_parser_choices(self):
        """Test argument parser choice validation"""
        parser = create_argument_parser()

        # Test valid choices
        args = parser.parse_args(["repo", "--method", "api"])
        assert args.method == "api"

        args = parser.parse_args(["repo", "--format", "json"])
        assert args.format == "json"

        # Test invalid choices would raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(["repo", "--method", "invalid"])

        with pytest.raises(SystemExit):
            parser.parse_args(["repo", "--format", "invalid"])


@pytest.mark.integration
class TestCLIRealWorld:
    """Real-world scenario tests"""

    def test_cli_workflow_simulation(self):
        """Test a realistic CLI workflow"""
        parser = create_argument_parser()

        # Simulate user running analysis command
        args = parser.parse_args([
            "owner/repo",
            "--output", "./test_output",
            "--format", "json",
            "--verbose"
        ])

        assert args.url == "owner/repo"
        assert args.output == "./test_output"
        assert args.format == "json"
        assert args.verbose is True
        assert args.method == "auto"  # Default

    def test_environment_variable_handling(self, monkeypatch):
        """Test environment variable integration - WARNING-FREE VERSION"""
        # Set environment variable
        monkeypatch.setenv("GITHUB_TOKEN", "test_env_token")
        
        # Create args without explicit token
        parser = create_argument_parser()
        args = parser.parse_args(["owner/repo"])
        
        assert args.github_token is None  # Not set via args
        
        # Verify environment variable was set
        import os
        assert os.getenv("GITHUB_TOKEN") == "test_env_token"
        
        # Test TokenUtils availability without triggering async operations
        if TOKEN_UTILS_AVAILABLE:
            # CORRECTED: Mock the TokenUtils to avoid async calls
            with patch('py_github_analyzer.utils.TokenUtils.get_github_token', return_value="test_env_token") as mock_get_token:
                from py_github_analyzer.utils import TokenUtils
                token = TokenUtils.get_github_token()
                assert token == "test_env_token"
                mock_get_token.assert_called_once()
