"""Property-based tests for LLM client retry logic."""

import time
from unittest.mock import Mock
from hypothesis import given, settings, strategies as st
import pytest

from docgen.llm import LLMClient, LLMError, RateLimitError
from docgen.models import LLMConfig


@settings(max_examples=100, deadline=15000)  # 15 second deadline for tests with sleep
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    num_failures=st.integers(min_value=0, max_value=4)
)
def test_retry_exponential_backoff(max_retries, num_failures):
    """
    Feature: docstring-generator, Property 13: For any rate limit error from an LLM 
    provider, the client should retry up to 3 times with exponentially increasing 
    wait times (2^attempt seconds).
    
    **Validates: Requirements 4.6**
    
    This property verifies that:
    1. The client retries up to max_retries times for rate limit errors
    2. Wait times follow exponential backoff pattern (2^attempt seconds)
    3. Successful responses after retries are returned correctly
    4. Failures after max_retries raise appropriate errors
    """
    # Ensure num_failures doesn't exceed max_retries
    num_failures = min(num_failures, max_retries)
    
    config = LLMConfig(
        provider='anthropic',
        model='claude-3-5-sonnet-20241022',
        api_key='test-key',
        max_retries=max_retries
    )
    client = LLMClient(config)
    
    # Mock the provider client
    client._provider_client = Mock()
    
    # Create side effects: num_failures rate limit errors, then success
    side_effects = [RateLimitError("Rate limited")] * num_failures
    if num_failures < max_retries:
        side_effects.append("Generated docstring")
    
    client._provider_client.generate.side_effect = side_effects
    
    if num_failures < max_retries:
        # Should succeed after retries
        start_time = time.time()
        result = client.generate("Test prompt")
        elapsed = time.time() - start_time
        
        assert result == "Generated docstring"
        assert client._provider_client.generate.call_count == num_failures + 1
        
        # Verify exponential backoff timing
        # Expected wait time: sum of 2^i for i in range(num_failures)
        # i.e., 2^0 + 2^1 + ... + 2^(num_failures-1)
        if num_failures > 0:
            expected_wait = sum(2 ** i for i in range(num_failures))
            # Allow some tolerance for execution time
            assert elapsed >= expected_wait - 0.5
    else:
        # Should fail after max_retries
        with pytest.raises(LLMError, match="Rate limit exceeded"):
            client.generate("Test prompt")
        
        assert client._provider_client.generate.call_count == max_retries


@settings(max_examples=100, deadline=15000)  # 15 second deadline for tests with sleep
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    failure_attempt=st.integers(min_value=0, max_value=4)
)
def test_retry_stops_at_max_attempts(max_retries, failure_attempt):
    """
    Property: The client should stop retrying after max_retries attempts,
    regardless of the error type (for retryable errors).
    
    **Validates: Requirements 4.6**
    """
    # Ensure failure_attempt is within max_retries
    failure_attempt = min(failure_attempt, max_retries - 1)
    
    config = LLMConfig(
        provider='anthropic',
        model='claude-3-5-sonnet-20241022',
        api_key='test-key',
        max_retries=max_retries
    )
    client = LLMClient(config)
    
    # Mock the provider client to always fail
    client._provider_client = Mock()
    client._provider_client.generate.side_effect = RateLimitError("Rate limited")
    
    with pytest.raises(LLMError):
        client.generate("Test prompt")
    
    # Should attempt exactly max_retries times
    assert client._provider_client.generate.call_count == max_retries


@settings(max_examples=100, deadline=15000)  # 15 second deadline for tests with sleep
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    success_attempt=st.integers(min_value=0, max_value=4)
)
def test_retry_succeeds_on_any_attempt(max_retries, success_attempt):
    """
    Property: If generation succeeds on any attempt (including the first),
    the client should return the result without further retries.
    
    **Validates: Requirements 4.6**
    """
    # Ensure success_attempt is within max_retries
    success_attempt = min(success_attempt, max_retries - 1)
    
    config = LLMConfig(
        provider='anthropic',
        model='claude-3-5-sonnet-20241022',
        api_key='test-key',
        max_retries=max_retries
    )
    client = LLMClient(config)
    
    # Mock the provider client
    client._provider_client = Mock()
    
    # Create side effects: failures until success_attempt, then success
    side_effects = [RateLimitError("Rate limited")] * success_attempt
    side_effects.append("Generated docstring")
    
    client._provider_client.generate.side_effect = side_effects
    
    result = client.generate("Test prompt")
    
    assert result == "Generated docstring"
    # Should stop after success
    assert client._provider_client.generate.call_count == success_attempt + 1


@settings(max_examples=100, deadline=15000)  # 15 second deadline for tests with sleep
@given(
    max_retries=st.integers(min_value=1, max_value=5)
)
def test_exponential_backoff_timing(max_retries):
    """
    Property: The wait time between retries should follow exponential backoff
    pattern with base 2 (2^attempt seconds).
    
    **Validates: Requirements 4.6**
    """
    config = LLMConfig(
        provider='anthropic',
        model='claude-3-5-sonnet-20241022',
        api_key='test-key',
        max_retries=max_retries
    )
    client = LLMClient(config)
    
    # Mock the provider client to fail max_retries-1 times, then succeed
    client._provider_client = Mock()
    num_failures = max_retries - 1
    side_effects = [RateLimitError("Rate limited")] * num_failures
    side_effects.append("Generated docstring")
    client._provider_client.generate.side_effect = side_effects
    
    start_time = time.time()
    result = client.generate("Test prompt")
    elapsed = time.time() - start_time
    
    assert result == "Generated docstring"
    
    # Calculate expected wait time: sum of 2^i for i in range(num_failures)
    if num_failures > 0:
        expected_wait = sum(2 ** i for i in range(num_failures))
        # Allow tolerance for execution overhead
        assert elapsed >= expected_wait - 0.5
        # Also check upper bound (shouldn't wait too long)
        assert elapsed <= expected_wait + 2.0


@settings(max_examples=100)
@given(
    prompt=st.text(min_size=1, max_size=1000)
)
def test_prompt_passed_to_provider(prompt):
    """
    Property: The prompt passed to generate() should be forwarded to the
    provider client without modification.
    
    **Validates: Requirements 4.4, 4.5**
    """
    config = LLMConfig(
        provider='anthropic',
        model='claude-3-5-sonnet-20241022',
        api_key='test-key',
        max_retries=3
    )
    client = LLMClient(config)
    
    # Mock the provider client
    client._provider_client = Mock()
    client._provider_client.generate.return_value = "Generated docstring"
    
    client.generate(prompt)
    
    # Verify the prompt was passed unchanged
    client._provider_client.generate.assert_called_once_with(prompt)


@settings(max_examples=100)
@given(
    max_retries=st.integers(min_value=1, max_value=5)
)
def test_empty_response_treated_as_error(max_retries):
    """
    Property: Empty or whitespace-only responses should be treated as errors.
    
    **Validates: Requirements 4.5**
    """
    config = LLMConfig(
        provider='anthropic',
        model='claude-3-5-sonnet-20241022',
        api_key='test-key',
        max_retries=max_retries
    )
    client = LLMClient(config)
    
    # Mock the provider client to return empty responses, then a valid one
    client._provider_client = Mock()
    # First attempt returns empty, subsequent attempts return valid response
    side_effects = [""] * (max_retries - 1) if max_retries > 1 else [""]
    side_effects.append("Valid docstring")
    client._provider_client.generate.side_effect = side_effects
    
    if max_retries > 1:
        # Should succeed after retries
        result = client.generate("Test prompt")
        assert result == "Valid docstring"
        assert client._provider_client.generate.call_count == max_retries
    else:
        # Should fail with only 1 retry
        with pytest.raises(LLMError, match="Empty response"):
            client.generate("Test prompt")
        assert client._provider_client.generate.call_count == 1
