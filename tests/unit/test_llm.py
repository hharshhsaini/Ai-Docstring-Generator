"""Unit tests for LLM client and provider implementations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from docgen.llm import (
    LLMClient,
    LLMError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    AnthropicClient,
    OpenAIClient,
    OllamaClient,
)
from docgen.models import LLMConfig


class TestProviderSelection:
    """Test provider-specific client instantiation."""
    
    def test_anthropic_provider_selection(self):
        """Test that Anthropic client is used when provider is 'anthropic'."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key'
        )
        client = LLMClient(config)
        
        assert isinstance(client._provider_client, AnthropicClient)
        assert client._provider_client.model == 'claude-3-5-sonnet-20241022'
    
    def test_openai_provider_selection(self):
        """Test that OpenAI client is used when provider is 'openai'."""
        config = LLMConfig(
            provider='openai',
            model='gpt-4',
            api_key='test-key'
        )
        client = LLMClient(config)
        
        assert isinstance(client._provider_client, OpenAIClient)
        assert client._provider_client.model == 'gpt-4'
    
    def test_ollama_provider_selection(self):
        """Test that Ollama client is used when provider is 'ollama'."""
        config = LLMConfig(
            provider='ollama',
            model='llama2',
            base_url='http://localhost:11434'
        )
        client = LLMClient(config)
        
        assert isinstance(client._provider_client, OllamaClient)
        assert client._provider_client.model == 'llama2'
    
    def test_unsupported_provider(self):
        """Test that unsupported provider raises ValueError."""
        # Create a mock config that bypasses Pydantic validation
        config = Mock(spec=LLMConfig)
        config.provider = 'unsupported'
        config.model = 'test-model'
        config.api_key = 'test-key'
        config.timeout = 30
        config.max_retries = 3
        
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMClient(config)


class TestAnthropicClient:
    """Test Anthropic provider client."""
    
    def test_missing_api_key(self):
        """Test that missing API key raises AuthenticationError."""
        with pytest.raises(AuthenticationError, match="API key is required"):
            AnthropicClient(model='claude-3-5-sonnet-20241022', api_key=None)
    
    def test_successful_generation(self):
        """Test successful text generation."""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Mock the Anthropic client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="Generated docstring")]
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client
            
            client = AnthropicClient(
                model='claude-3-5-sonnet-20241022',
                api_key='test-key'
            )
            
            result = client.generate("Test prompt")
            
            assert result == "Generated docstring"
            mock_client.messages.create.assert_called_once()
    
    def test_rate_limit_error(self):
        """Test that rate limit error is properly mapped."""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            with patch('anthropic.RateLimitError', Exception):
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client
                
                import anthropic
                mock_client.messages.create.side_effect = anthropic.RateLimitError("Rate limited")
                
                client = AnthropicClient(
                    model='claude-3-5-sonnet-20241022',
                    api_key='test-key'
                )
                
                with pytest.raises(RateLimitError, match="rate limit"):
                    client.generate("Test prompt")
    
    def test_authentication_error(self):
        """Test that authentication error is properly mapped."""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            with patch('anthropic.AuthenticationError', Exception):
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client
                
                import anthropic
                mock_client.messages.create.side_effect = anthropic.AuthenticationError("Invalid key")
                
                client = AnthropicClient(
                    model='claude-3-5-sonnet-20241022',
                    api_key='test-key'
                )
                
                with pytest.raises(AuthenticationError, match="Invalid.*API key"):
                    client.generate("Test prompt")
    
    def test_timeout_error(self):
        """Test that timeout error is properly mapped."""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            with patch('anthropic.APITimeoutError', Exception):
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client
                
                import anthropic
                mock_client.messages.create.side_effect = anthropic.APITimeoutError("Timeout")
                
                client = AnthropicClient(
                    model='claude-3-5-sonnet-20241022',
                    api_key='test-key'
                )
                
                with pytest.raises(TimeoutError, match="timed out"):
                    client.generate("Test prompt")


class TestOpenAIClient:
    """Test OpenAI provider client."""
    
    def test_missing_api_key(self):
        """Test that missing API key raises AuthenticationError."""
        with pytest.raises(AuthenticationError, match="API key is required"):
            OpenAIClient(model='gpt-4', api_key=None)
    
    def test_successful_generation(self):
        """Test successful text generation."""
        with patch('openai.OpenAI') as mock_openai_class:
            # Mock the OpenAI client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Generated docstring"))]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            client = OpenAIClient(model='gpt-4', api_key='test-key')
            
            result = client.generate("Test prompt")
            
            assert result == "Generated docstring"
            mock_client.chat.completions.create.assert_called_once()
    
    def test_rate_limit_error(self):
        """Test that rate limit error is properly mapped."""
        with patch('openai.OpenAI') as mock_openai_class:
            with patch('openai.RateLimitError', Exception):
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                
                import openai
                mock_client.chat.completions.create.side_effect = openai.RateLimitError("Rate limited")
                
                client = OpenAIClient(model='gpt-4', api_key='test-key')
                
                with pytest.raises(RateLimitError, match="rate limit"):
                    client.generate("Test prompt")
    
    def test_authentication_error(self):
        """Test that authentication error is properly mapped."""
        with patch('openai.OpenAI') as mock_openai_class:
            with patch('openai.AuthenticationError', Exception):
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                
                import openai
                mock_client.chat.completions.create.side_effect = openai.AuthenticationError("Invalid key")
                
                client = OpenAIClient(model='gpt-4', api_key='test-key')
                
                with pytest.raises(AuthenticationError, match="Invalid.*API key"):
                    client.generate("Test prompt")
    
    def test_timeout_error(self):
        """Test that timeout error is properly mapped."""
        with patch('openai.OpenAI') as mock_openai_class:
            with patch('openai.APITimeoutError', Exception):
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                
                import openai
                mock_client.chat.completions.create.side_effect = openai.APITimeoutError("Timeout")
                
                client = OpenAIClient(model='gpt-4', api_key='test-key')
                
                with pytest.raises(TimeoutError, match="timed out"):
                    client.generate("Test prompt")


class TestOllamaClient:
    """Test Ollama provider client."""
    
    def test_successful_generation(self):
        """Test successful text generation."""
        with patch('requests.post') as mock_post:
            # Mock the requests.post response
            mock_response = Mock()
            mock_response.json.return_value = {"response": "Generated docstring"}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            client = OllamaClient(model='llama2', base_url='http://localhost:11434')
            
            result = client.generate("Test prompt")
            
            assert result == "Generated docstring"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == 'http://localhost:11434/api/generate'
            assert call_args[1]['json']['model'] == 'llama2'
            assert call_args[1]['json']['stream'] is False
    
    def test_timeout_error(self):
        """Test that timeout error is properly mapped."""
        with patch('requests.post') as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.Timeout("Timeout")
            
            client = OllamaClient(model='llama2')
            
            with pytest.raises(TimeoutError, match="timed out"):
                client.generate("Test prompt")
    
    def test_rate_limit_error(self):
        """Test that 429 status code is mapped to RateLimitError."""
        with patch('requests.post') as mock_post:
            import requests
            mock_response = Mock()
            mock_response.status_code = 429
            http_error = requests.exceptions.HTTPError("Rate limited")
            http_error.response = mock_response
            mock_post.side_effect = http_error
            
            client = OllamaClient(model='llama2')
            
            with pytest.raises(RateLimitError, match="rate limit"):
                client.generate("Test prompt")
    
    def test_authentication_error(self):
        """Test that 401/403 status codes are mapped to AuthenticationError."""
        with patch('requests.post') as mock_post:
            import requests
            mock_response = Mock()
            mock_response.status_code = 401
            http_error = requests.exceptions.HTTPError("Unauthorized")
            http_error.response = mock_response
            mock_post.side_effect = http_error
            
            client = OllamaClient(model='llama2')
            
            with pytest.raises(AuthenticationError, match="authentication failed"):
                client.generate("Test prompt")
    
    def test_base_url_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = OllamaClient(model='llama2', base_url='http://localhost:11434/')
        
        assert client.base_url == 'http://localhost:11434'


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    def test_successful_generation_no_retry(self):
        """Test that successful generation doesn't retry."""
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
        
        result = client.generate("Test prompt")
        
        assert result == "Generated docstring"
        assert client._provider_client.generate.call_count == 1
    
    def test_retry_on_rate_limit(self):
        """Test that rate limit errors trigger retry with exponential backoff."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            max_retries=3
        )
        client = LLMClient(config)
        
        # Mock the provider client to fail twice then succeed
        client._provider_client = Mock()
        client._provider_client.generate.side_effect = [
            RateLimitError("Rate limited"),
            RateLimitError("Rate limited"),
            "Generated docstring"
        ]
        
        start_time = time.time()
        result = client.generate("Test prompt")
        elapsed = time.time() - start_time
        
        assert result == "Generated docstring"
        assert client._provider_client.generate.call_count == 3
        # Should wait 2^0 + 2^1 = 1 + 2 = 3 seconds
        assert elapsed >= 3.0
    
    def test_max_retries_exceeded(self):
        """Test that max retries is respected."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            max_retries=3
        )
        client = LLMClient(config)
        
        # Mock the provider client to always fail
        client._provider_client = Mock()
        client._provider_client.generate.side_effect = RateLimitError("Rate limited")
        
        with pytest.raises(LLMError, match="Rate limit exceeded after 3 attempts"):
            client.generate("Test prompt")
        
        assert client._provider_client.generate.call_count == 3
    
    def test_no_retry_on_authentication_error(self):
        """Test that authentication errors don't trigger retry."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            max_retries=3
        )
        client = LLMClient(config)
        
        # Mock the provider client to fail with auth error
        client._provider_client = Mock()
        client._provider_client.generate.side_effect = AuthenticationError("Invalid key")
        
        with pytest.raises(AuthenticationError):
            client.generate("Test prompt")
        
        # Should not retry
        assert client._provider_client.generate.call_count == 1
    
    def test_no_retry_on_timeout_error(self):
        """Test that timeout errors don't trigger retry."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            max_retries=3
        )
        client = LLMClient(config)
        
        # Mock the provider client to fail with timeout
        client._provider_client = Mock()
        client._provider_client.generate.side_effect = TimeoutError("Timeout")
        
        with pytest.raises(TimeoutError):
            client.generate("Test prompt")
        
        # Should not retry
        assert client._provider_client.generate.call_count == 1
    
    def test_retry_on_generic_error(self):
        """Test that generic errors trigger retry."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            max_retries=2
        )
        client = LLMClient(config)
        
        # Mock the provider client to fail then succeed
        client._provider_client = Mock()
        client._provider_client.generate.side_effect = [
            Exception("Temporary error"),
            "Generated docstring"
        ]
        
        result = client.generate("Test prompt")
        
        assert result == "Generated docstring"
        assert client._provider_client.generate.call_count == 2
    
    def test_empty_response_error(self):
        """Test that empty responses are treated as errors."""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            max_retries=2
        )
        client = LLMClient(config)
        
        # Mock the provider client to return empty string
        client._provider_client = Mock()
        client._provider_client.generate.return_value = ""
        
        with pytest.raises(LLMError, match="Empty response"):
            client.generate("Test prompt")
