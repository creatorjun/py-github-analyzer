"""
FINAL CORRECTED VERSION - All 4 failures fixed
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import AsyncExitStack
import httpx

from py_github_analyzer.async_github_client import AsyncGitHubClient, AsyncRateLimitManager, AsyncGitHubSession
from py_github_analyzer.exceptions import (
    NetworkError, RateLimitExceededError, AuthenticationError,
    PrivateRepositoryError, RepositoryTooLargeError
)


@pytest.mark.unit
class TestAsyncRateLimitManager:
    """Test AsyncRateLimitManager functionality"""

    def test_rate_limit_manager_init_with_token(self):
        """Test rate limit manager initialization with token"""
        manager = AsyncRateLimitManager(token="test_token")
        assert manager.token == "test_token"
        assert manager.limit == 5000
        assert manager.remaining == 5000

    def test_rate_limit_manager_init_without_token(self):
        """Test rate limit manager initialization without token"""
        manager = AsyncRateLimitManager()
        assert manager.token is None
        assert manager.limit == 60
        assert manager.remaining == 60

    @pytest.mark.asyncio
    async def test_update_from_headers(self):
        """Test updating rate limit info from response headers"""
        manager = AsyncRateLimitManager()
        headers = {
            'x-ratelimit-limit': '100',
            'x-ratelimit-remaining': '95',
            'x-ratelimit-reset': '1234567890'
        }
        
        await manager.update_from_headers(headers)
        assert manager.limit == 100
        assert manager.remaining == 95
        assert manager.reset_time == 1234567890

    @pytest.mark.asyncio
    async def test_check_rate_limit_sufficient(self):
        """Test rate limit check with sufficient calls"""
        manager = AsyncRateLimitManager()
        manager.remaining = 100
        
        result = await manager.check_rate_limit(10)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_insufficient(self):
        """Test rate limit check with insufficient calls"""
        manager = AsyncRateLimitManager()
        manager.remaining = 3  # Less than required + buffer (5)
        
        result = await manager.check_rate_limit(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_consume_calls(self):
        """Test consuming API calls"""
        manager = AsyncRateLimitManager()
        manager.remaining = 100
        
        await manager.consume_calls(10)
        assert manager.remaining == 90

    @pytest.mark.asyncio
    async def test_consume_calls_no_negative(self):
        """Test that consuming calls doesn't go negative"""
        manager = AsyncRateLimitManager()
        manager.remaining = 5
        
        await manager.consume_calls(10)
        assert manager.remaining == 0


@pytest.mark.unit
class TestAsyncGitHubSession:
    """Test AsyncGitHubSession functionality"""

    def test_session_init_with_token(self):
        """Test session initialization with token"""
        with patch('py_github_analyzer.async_github_client.httpx.AsyncClient') as mock_client:
            session = AsyncGitHubSession(token="test_token", timeout=30)
            assert session.token == "test_token"
            assert session.timeout == 30
            mock_client.assert_called_once()

    def test_session_init_without_httpx(self):
        """Test session initialization without httpx available"""
        with patch('py_github_analyzer.async_github_client.HTTPX_AVAILABLE', False):
            with pytest.raises(ImportError, match="httpx library is required"):
                AsyncGitHubSession()

    @pytest.mark.asyncio
    async def test_session_request_success(self, mock_httpx_response):
        """Test successful HTTP request"""
        mock_response = mock_httpx_response(200, {"test": "data"})
        
        with patch('py_github_analyzer.async_github_client.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            session = AsyncGitHubSession()
            response = await session.request('GET', 'https://api.github.com/test')
            
            assert response.status_code == 200
            mock_client.request.assert_called_once_with('GET', 'https://api.github.com/test')

    @pytest.mark.asyncio
    async def test_session_request_error_handling(self):
        """Test HTTP request error handling - CORRECTED TO CATCH ACTUAL EXCEPTION"""
        with patch('py_github_analyzer.async_github_client.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.side_effect = httpx.RequestError("Connection failed")
            mock_client_class.return_value = mock_client
            
            session = AsyncGitHubSession()
            # CORRECTED: The session catches httpx.RequestError and raises NetworkError
            with pytest.raises(NetworkError):
                await session.request('GET', 'https://api.github.com/test')


@pytest.mark.unit
class TestAsyncGitHubClient:
    """Test AsyncGitHubClient main functionality"""

    @pytest.fixture
    def github_client_sync(self, test_token, mock_logger):
        """Create AsyncGitHubClient for NON-ASYNC testing"""
        with patch('py_github_analyzer.async_github_client.AsyncGitHubSession'):
            client = AsyncGitHubClient(token=test_token, logger=mock_logger)
            client.session = AsyncMock()
            client._semaphore = asyncio.Semaphore(10)
            return client

    @pytest.mark.asyncio
    async def test_client_initialization(self, test_token, mock_logger):
        """Test client initialization"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        assert client.token == test_token
        assert client.logger == mock_logger
        assert isinstance(client.rate_limit_manager, AsyncRateLimitManager)

    @pytest.mark.asyncio
    async def test_context_manager(self, test_token, mock_logger):
        """Test client as context manager"""
        with patch('py_github_analyzer.async_github_client.AsyncGitHubSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with AsyncGitHubClient(token=test_token, logger=mock_logger) as client:
                assert client.session is not None
                assert client._semaphore is not None
            
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_repository_info_success(self, test_token, mock_logger, mock_httpx_response, mock_github_api_responses):
        """Test successful repository info retrieval"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        mock_response = mock_httpx_response(200, mock_github_api_responses['repository_info'])
        mock_response.headers = mock_github_api_responses['rate_limit_headers']
        
        client.session.get.return_value = mock_response
        client.rate_limit_manager.execute_api_call = AsyncMock(return_value=mock_response)
        
        repo_info = await client.get_repository_info('test-owner', 'test-repo')
        
        assert repo_info['name'] == 'test-repo'
        assert repo_info['full_name'] == 'test-owner/test-repo'
        assert repo_info['language'] == 'Python'
        assert repo_info['private'] is False

    @pytest.mark.asyncio
    async def test_get_repository_info_safe_mode(self, test_token, mock_logger, mock_httpx_response):
        """Test repository info retrieval in safe mode"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        mock_response = mock_httpx_response(404)
        client.session.get.return_value = mock_response
        client.rate_limit_manager.track_safe_api_call = AsyncMock()
        
        repo_info = await client.get_repository_info('test-owner', 'test-repo', safe_mode=True)
        
        assert repo_info['name'] == 'test-repo'
        assert repo_info['full_name'] == 'test-owner/test-repo'
        assert repo_info['language'] == 'Unknown'
        client.rate_limit_manager.track_safe_api_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_default_branch(self, test_token, mock_logger):
        """Test default branch detection"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        
        # Mock ZIP availability tests
        client._test_zip_availability = AsyncMock()
        client._test_zip_availability.side_effect = [False, True, False]  # 'master' available
        
        branch = await client.detect_default_branch('test-owner', 'test-repo')
        assert branch == 'master'  # Second in priority list

    @pytest.mark.asyncio
    async def test_test_zip_availability_success(self, test_token, mock_logger, mock_httpx_response):
        """Test ZIP availability test success"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        mock_response = mock_httpx_response(200)
        client.session.get.return_value = mock_response
        
        result = await client._test_zip_availability('test-owner', 'test-repo', 'main')
        assert result is True

    @pytest.mark.asyncio
    async def test_test_zip_availability_failure(self, test_token, mock_logger, mock_httpx_response):
        """Test ZIP availability test failure"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        mock_response = mock_httpx_response(404)
        client.session.get.return_value = mock_response
        
        result = await client._test_zip_availability('test-owner', 'test-repo', 'main')
        assert result is False

    @pytest.mark.asyncio
    async def test_download_repository_zip_success(self, test_token, mock_logger, sample_zip_content):
        """Test successful ZIP download - COMPLETELY CORRECTED CONTEXT MANAGER MOCK"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        # CORRECTED: Create a proper async context manager mock
        class MockStreamContext:
            def __init__(self, response_mock):
                self.response_mock = response_mock
                
            async def __aenter__(self):
                return self.response_mock
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        # Create the mock response
        mock_stream_response = AsyncMock()
        mock_stream_response.status_code = 200
        mock_stream_response.is_success = True
        mock_stream_response.headers = {'content-length': str(len(sample_zip_content))}
        
        async def mock_aiter_bytes(chunk_size):
            for i in range(0, len(sample_zip_content), chunk_size):
                yield sample_zip_content[i:i + chunk_size]
        
        mock_stream_response.aiter_bytes = mock_aiter_bytes
        
        # CORRECTED: Mock the stream method to return our context manager
        mock_context = MockStreamContext(mock_stream_response)
        client.session.client = AsyncMock()
        client.session.client.stream = MagicMock(return_value=mock_context)
        
        # Mock ZIP extraction
        client._extract_zip_contents_async = AsyncMock(return_value=[
            {'path': 'main.py', 'content': 'print("hello")', 'size': 15, 'priority': 95}
        ])
        
        files = await client.download_repository_zip('test-owner', 'test-repo', 'main')
        
        assert len(files) == 1
        assert files[0]['path'] == 'main.py'
        client.session.client.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_repository_zip_private_repo_error(self, test_token, mock_logger):
        """Test ZIP download with private repository error - CORRECTED CONTEXT MANAGER"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        # CORRECTED: Create proper context manager mock
        class MockStreamContext:
            def __init__(self, response_mock):
                self.response_mock = response_mock
                
            async def __aenter__(self):
                return self.response_mock
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        # Mock 404 response for main branch
        mock_stream_response = AsyncMock()
        mock_stream_response.status_code = 404
        mock_stream_response.is_success = False
        
        mock_context = MockStreamContext(mock_stream_response)
        client.session.client = AsyncMock()
        client.session.client.stream = MagicMock(return_value=mock_context)
        
        # Mock all alternative branches failing
        client._try_alternative_zip = AsyncMock()
        client._try_alternative_zip.side_effect = [Exception("404"), Exception("404"), Exception("404")]
        
        with pytest.raises(PrivateRepositoryError):
            await client.download_repository_zip('test-owner', 'private-repo', 'main')

    @pytest.mark.asyncio
    async def test_download_repository_zip_too_large(self, test_token, mock_logger):
        """Test ZIP download size limit - CORRECTED CONTEXT MANAGER"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        
        # CORRECTED: Create proper context manager mock  
        class MockStreamContext:
            def __init__(self, response_mock):
                self.response_mock = response_mock
                
            async def __aenter__(self):
                return self.response_mock
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        large_size = str(1024 * 1024 * 1024)  # 1GB
        mock_stream_response = AsyncMock()
        mock_stream_response.status_code = 200
        mock_stream_response.is_success = True
        mock_stream_response.headers = {'content-length': large_size}
        
        mock_context = MockStreamContext(mock_stream_response)
        client.session.client = AsyncMock()
        client.session.client.stream = MagicMock(return_value=mock_context)
        
        with pytest.raises(RepositoryTooLargeError):
            await client.download_repository_zip('test-owner', 'huge-repo', 'main')

    def test_extract_zip_contents_sync(self, github_client_sync, sample_zip_content):
        """Test synchronous ZIP extraction"""
        files = github_client_sync._extract_zip_contents_sync(sample_zip_content, 'test-repo-main')
        
        assert len(files) >= 1  # Should have at least some files
        assert all('path' in f for f in files)
        assert all('content' in f for f in files)

    @pytest.mark.asyncio
    async def test_get_repository_tree_api_success(self, test_token, mock_logger, mock_httpx_response, mock_github_api_responses):
        """Test successful repository tree retrieval via API"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        client._semaphore = asyncio.Semaphore(10)
        
        # Add missing 'sha' field to mock data
        corrected_tree_response = {
            'tree': [
                {'path': 'main.py', 'size': 45, 'type': 'blob', 'sha': 'abc123', 'url': 'test-url'},
                {'path': 'requirements.txt', 'size': 20, 'type': 'blob', 'sha': 'def456', 'url': 'test-url'}
            ]
        }
        
        mock_response = mock_httpx_response(200, corrected_tree_response)
        mock_response.headers = mock_github_api_responses['rate_limit_headers']
        
        client.rate_limit_manager.execute_api_call = AsyncMock(return_value=mock_response)
        
        files = await client.get_repository_tree_api('test-owner', 'test-repo', 'main')
        
        assert len(files) == 2
        assert files[0]['path'] == 'main.py'
        assert files[1]['path'] == 'requirements.txt'
        assert files[0]['sha'] == 'abc123'

    @pytest.mark.asyncio
    async def test_download_single_file_success(self, test_token, mock_logger, mock_httpx_response):
        """Test successful single file download"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        client._semaphore = asyncio.Semaphore(10)
        
        file_content = b"print('Hello, World!')"
        mock_response = mock_httpx_response(200, content=file_content)
        mock_response.headers = {'x-ratelimit-remaining': '4999'}
        
        client.rate_limit_manager.execute_api_call = AsyncMock(return_value=mock_response)
        
        file_info = {
            'path': 'main.py',
            'download_url': 'https://raw.githubusercontent.com/test-owner/test-repo/main/main.py'
        }
        
        result = await client.download_single_file(file_info)
        
        assert result is not None
        assert result['path'] == 'main.py'
        assert 'Hello, World!' in result['content']

    @pytest.mark.asyncio
    async def test_download_single_file_too_large(self, test_token, mock_logger, mock_httpx_response):
        """Test single file download size limit"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        client._semaphore = asyncio.Semaphore(10)
        
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        mock_response = mock_httpx_response(200, content=large_content)
        
        client.rate_limit_manager.execute_api_call = AsyncMock(return_value=mock_response)
        
        file_info = {
            'path': 'large_file.txt',
            'download_url': 'https://raw.githubusercontent.com/test-owner/test-repo/main/large_file.txt'
        }
        
        result = await client.download_single_file(file_info)
        assert result is None  # Should reject large files

    @pytest.mark.asyncio
    async def test_download_files_concurrently(self, test_token, mock_logger):
        """Test concurrent file downloads"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        
        # Mock successful downloads
        client.download_single_file = AsyncMock()
        client.download_single_file.side_effect = [
            {'path': 'file1.py', 'content': 'content1', 'size': 10},
            {'path': 'file2.py', 'content': 'content2', 'size': 10},
            None  # One failed download
        ]
        
        files = [
            {'path': 'file1.py', 'download_url': 'url1'},
            {'path': 'file2.py', 'download_url': 'url2'},
            {'path': 'file3.py', 'download_url': 'url3'}
        ]
        
        results = await client.download_files_concurrently(files)
        
        assert len(results) == 2  # Two successful downloads
        assert client.download_single_file.call_count == 3

    def test_filter_and_prioritize_files(self, github_client_sync):
        """Test file filtering and prioritization"""
        files = [
            {'path': 'main.py', 'size': 100},
            {'path': '.git/config', 'size': 50},  # Should be excluded
            {'path': 'image.png', 'size': 200},  # Should be excluded (binary)
            {'path': 'README.md', 'size': 150},
            {'path': 'huge_file.txt', 'size': 20 * 1024 * 1024}  # Should be excluded (too large)
        ]
        
        filtered = github_client_sync._filter_and_prioritize_files(files)
        paths = [f['path'] for f in filtered]
        
        assert 'main.py' in paths
        assert 'README.md' in paths
        assert '.git/config' not in paths
        assert 'huge_file.txt' not in paths

    def test_should_try_api_fallback(self, github_client_sync):
        """Test API fallback decision logic"""
        # Should fallback
        assert github_client_sync._should_try_api_fallback(PrivateRepositoryError("Private repo", "url"))
        assert github_client_sync._should_try_api_fallback(NetworkError("Network error"))
        
        # Should not fallback
        assert not github_client_sync._should_try_api_fallback(AuthenticationError("Auth failed"))
        assert not github_client_sync._should_try_api_fallback(RateLimitExceededError("Rate limit", 123, 0))

    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, test_token, mock_logger):
        """Test rate limit info retrieval"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.rate_limit_manager.limit = 5000
        client.rate_limit_manager.remaining = 4500
        client.rate_limit_manager.reset_time = 1234567890
        
        info = await client.get_rate_limit_info()
        
        assert info['limit'] == 5000
        assert info['remaining'] == 4500
        assert info['reset_time'] == 1234567890
        assert 'reset_in_seconds' in info


@pytest.mark.integration
class TestAsyncGitHubClientIntegration:
    """Integration tests for AsyncGitHubClient"""

    @pytest.mark.asyncio
    async def test_analyze_repository_zip_method(self, test_token, mock_logger):
        """Test full repository analysis using ZIP method"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        client._semaphore = asyncio.Semaphore(10)
        
        # Mock ZIP download success
        client.download_repository_zip = AsyncMock(return_value=[
            {'path': 'main.py', 'content': 'print("test")', 'size': 15, 'priority': 95}
        ])
        client.get_repository_info = AsyncMock(return_value={
            'name': 'test-repo', 'language': 'Python'
        })
        
        files, repo_info = await client.analyze_repository('test-owner', 'test-repo')
        
        assert len(files) == 1
        assert files[0]['path'] == 'main.py'
        assert repo_info['name'] == 'test-repo'

    @pytest.mark.asyncio
    async def test_analyze_repository_api_fallback(self, test_token, mock_logger):
        """Test repository analysis with API fallback"""
        client = AsyncGitHubClient(token=test_token, logger=mock_logger)
        client.session = AsyncMock()
        client._semaphore = asyncio.Semaphore(10)
        
        # Mock ZIP failure and API success
        client.download_repository_zip = AsyncMock(side_effect=PrivateRepositoryError("Private", "url"))
        client._try_api_method = AsyncMock(return_value=(
            [{'path': 'main.py', 'content': 'print("api")', 'size': 15}],
            {'name': 'test-repo', 'language': 'Python'}
        ))
        client._should_try_api_fallback = MagicMock(return_value=True)
        
        files, repo_info = await client.analyze_repository('test-owner', 'test-repo')
        
        assert len(files) == 1
        assert files[0]['path'] == 'main.py'
        client._try_api_method.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_repository_no_token_private_repo(self, mock_logger):
        """Test repository analysis without token for private repo"""
        client = AsyncGitHubClient(token=None, logger=mock_logger)
        client.session = AsyncMock()
        client._semaphore = asyncio.Semaphore(10)
        client.download_repository_zip = AsyncMock(side_effect=PrivateRepositoryError("Private", "url"))
        client.get_repository_info = AsyncMock(return_value={'name': 'repo'})
        
        with pytest.raises(PrivateRepositoryError):
            await client.analyze_repository('test-owner', 'private-repo')
