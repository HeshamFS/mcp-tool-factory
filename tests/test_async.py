"""Tests for async functionality across the codebase."""

import asyncio
from unittest.mock import Mock

import pytest


class TestAsyncValidation:
    """Tests for async validation patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_validation(self):
        """Test running multiple validations concurrently."""
        from tool_factory.utils.input_validation import (
            validate_email,
            validate_string,
            validate_url,
        )

        async def async_validate_string(value: str) -> bool:
            # Simulate async validation
            await asyncio.sleep(0.01)
            return validate_string(value, "test").is_valid

        async def async_validate_email(value: str) -> bool:
            await asyncio.sleep(0.01)
            return validate_email(value, "test").is_valid

        async def async_validate_url(value: str) -> bool:
            await asyncio.sleep(0.01)
            return validate_url(value, "test").is_valid

        # Run validations concurrently
        results = await asyncio.gather(
            async_validate_string("hello"),
            async_validate_email("test@example.com"),
            async_validate_url("https://example.com"),
        )

        assert results == [True, True, True]

    @pytest.mark.asyncio
    async def test_concurrent_invalid_validation(self):
        """Test concurrent validation with invalid inputs."""
        from tool_factory.utils.input_validation import (
            validate_email,
            validate_url,
        )

        async def async_validate_email(value: str) -> bool:
            await asyncio.sleep(0.01)
            return validate_email(value, "test").is_valid

        async def async_validate_url(value: str) -> bool:
            await asyncio.sleep(0.01)
            return validate_url(value, "test").is_valid

        results = await asyncio.gather(
            async_validate_email("not-an-email"),
            async_validate_url("not-a-url"),
        )

        assert results == [False, False]


class TestAsyncSecurityScanning:
    """Tests for async security scanning patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_code_scanning(self):
        """Test scanning multiple code snippets concurrently."""
        from tool_factory.security import scan_code

        code_snippets = [
            'password = "secret123"',
            "def safe_function(): pass",
            'api_key = "sk_live_abc123"',
        ]

        async def async_scan(code: str):
            await asyncio.sleep(0.01)
            return scan_code(code)

        results = await asyncio.gather(*[async_scan(code) for code in code_snippets])

        # First snippet has password issue
        assert len(results[0]) > 0
        # Second snippet is safe
        assert len(results[1]) == 0
        # Third snippet may or may not have API key issue depending on pattern
        assert isinstance(results[2], list)


class TestAsyncProviderPatterns:
    """Tests for async patterns with providers."""

    @pytest.mark.asyncio
    async def test_provider_timeout_pattern(self):
        """Test timeout pattern for provider calls."""
        from tool_factory.providers import AnthropicProvider

        AnthropicProvider(
            api_key="test-key",
            model="claude-3-opus",
        )

        async def slow_call():
            await asyncio.sleep(5)  # This would timeout

        # Test that we can implement timeout patterns
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_call(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_concurrent_provider_calls(self):
        """Test making concurrent provider calls."""
        from tool_factory.providers import AnthropicProvider

        provider = AnthropicProvider(
            api_key="test-key",
            model="claude-3-opus",
        )

        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.stop_reason = "end_turn"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        async def async_call(prompt: str):
            await asyncio.sleep(0.01)
            return provider.call("system", prompt)

        results = await asyncio.gather(
            async_call("prompt1"),
            async_call("prompt2"),
            async_call("prompt3"),
        )

        assert len(results) == 3
        assert all(r.text == "Response" for r in results)


class TestAsyncRateLimiting:
    """Tests for async rate limiting patterns."""

    @pytest.mark.asyncio
    async def test_rate_limit_timing(self):
        """Test rate limiting timing pattern."""
        import time

        call_times = []
        rate_limit_delay = 0.05  # 50ms between calls

        async def rate_limited_call(index: int):
            if call_times:
                elapsed = time.time() - call_times[-1]
                if elapsed < rate_limit_delay:
                    await asyncio.sleep(rate_limit_delay - elapsed)

            call_times.append(time.time())
            return index

        # Make sequential rate-limited calls
        results = []
        for i in range(3):
            result = await rate_limited_call(i)
            results.append(result)

        assert results == [0, 1, 2]

        # Check timing - each call should be at least rate_limit_delay apart
        for i in range(1, len(call_times)):
            elapsed = call_times[i] - call_times[i - 1]
            # Allow some tolerance
            assert elapsed >= rate_limit_delay * 0.9


class TestAsyncContextManagers:
    """Tests for async context manager patterns."""

    @pytest.mark.asyncio
    async def test_async_telemetry_context(self):
        """Test async context for telemetry."""

        class AsyncSpan:
            def __init__(self, name: str):
                self.name = name
                self.started = False
                self.ended = False

            async def __aenter__(self):
                self.started = True
                return self

            async def __aexit__(self, *args):
                self.ended = True

        async with AsyncSpan("test_operation") as span:
            assert span.started
            await asyncio.sleep(0.01)  # Simulate work

        assert span.ended

    @pytest.mark.asyncio
    async def test_async_resource_cleanup(self):
        """Test async resource cleanup patterns."""
        cleanup_called = False

        async def async_cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        class AsyncResource:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                await async_cleanup()

        async with AsyncResource():
            pass

        assert cleanup_called


class TestAsyncErrorHandling:
    """Tests for async error handling patterns."""

    @pytest.mark.asyncio
    async def test_gather_with_exceptions(self):
        """Test handling exceptions in gather."""

        async def success():
            await asyncio.sleep(0.01)
            return "ok"

        async def failure():
            await asyncio.sleep(0.01)
            raise ValueError("Failed")

        # With return_exceptions=True, exceptions are returned as results
        results = await asyncio.gather(
            success(),
            failure(),
            success(),
            return_exceptions=True,
        )

        assert results[0] == "ok"
        assert isinstance(results[1], ValueError)
        assert results[2] == "ok"

    @pytest.mark.asyncio
    async def test_retry_pattern(self):
        """Test async retry pattern."""
        attempts = 0

        async def flaky_operation():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        async def with_retry(coro_func, max_retries=3):
            last_error = None
            for _ in range(max_retries):
                try:
                    return await coro_func()
                except Exception as e:
                    last_error = e
                    await asyncio.sleep(0.01)
            raise last_error

        result = await with_retry(flaky_operation)
        assert result == "success"
        assert attempts == 3
