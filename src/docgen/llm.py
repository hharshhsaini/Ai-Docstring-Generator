"""LLM client with provider abstraction and retry logic.

This module provides a unified interface to multiple LLM providers (Anthropic, OpenAI, Ollama)
with automatic retry logic, exponential backoff, and error handling.
"""

import time
from typing import Protocol
from pydantic import BaseModel

from docgen.models import LLMConfig, LLMResponse


# Exception classes
class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class RateLimitError(LLMError):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(LLMError):
    """Raised when API key is invalid."""
    pass


class TimeoutError(LLMError):
    """Raised when request times out."""
    pass


# Provider protocol
class LLMProvider(Protocol):
    """Protocol for LLM provider implementations."""
    
    def generate(self, prompt: str) -> str:
        """Generate text from prompt.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails
        """
        ...


class LLMClient:
    """Unified LLM client with provider abstraction and retry logic.
    
    This client provides a common interface to multiple LLM providers with
    automatic retry logic, exponential backoff for rate limits, and response
    validation.
    
    Attributes:
        config: LLM configuration
        _provider_client: Provider-specific client instance
    """
    
    def __init__(self, config: LLMConfig):
        """Initialize LLM client with configuration.
        
        Args:
            config: LLM configuration including provider, model, and credentials
        """
        self.config = config
        self._provider_client = self._create_provider_client()
    
    def _create_provider_client(self) -> LLMProvider:
        """Factory method to instantiate provider-specific client.
        
        Returns:
            Provider-specific client instance
            
        Raises:
            ValueError: If provider is not supported
        """
        if self.config.provider == "anthropic":
            return AnthropicClient(
                model=self.config.model,
                api_key=self.config.api_key,
                timeout=self.config.timeout
            )
        elif self.config.provider == "openai":
            return OpenAIClient(
                model=self.config.model,
                api_key=self.config.api_key,
                timeout=self.config.timeout
            )
        elif self.config.provider == "ollama":
            return OllamaClient(
                model=self.config.model,
                base_url=self.config.base_url or "http://localhost:11434",
                timeout=self.config.timeout
            )
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    def generate(self, prompt: str) -> str:
        """Generate docstring from prompt with retry logic.
        
        Args:
            prompt: Formatted prompt text
            
        Returns:
            Generated docstring text
            
        Raises:
            LLMError: If generation fails after all retries
        """
        return self._generate_with_retry(prompt)
    
    def _generate_with_retry(self, prompt: str) -> str:
        """Generate with exponential backoff retry logic.
        
        Implements exponential backoff with 2^attempt seconds wait time.
        Retries up to max_retries times for rate limit errors.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails after all retries
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = self._provider_client.generate(prompt)
                
                # Validate response is not empty
                if not response or not response.strip():
                    # Treat empty response as a retryable error
                    raise LLMError("Empty response from LLM provider")
                
                return response
                
            except RateLimitError as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise LLMError(
                        f"Rate limit exceeded after {self.config.max_retries} attempts: {e}"
                    ) from e
            
            except (AuthenticationError, TimeoutError) as e:
                # Don't retry authentication or timeout errors
                raise
            
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    # Brief wait before retry for other errors
                    time.sleep(1)
                    continue
                else:
                    raise LLMError(
                        f"Failed after {self.config.max_retries} attempts: {e}"
                    ) from e
        
        # Should not reach here, but just in case
        if last_exception:
            raise LLMError(f"Failed after {self.config.max_retries} attempts") from last_exception
        raise LLMError("Unknown error during generation")


class AnthropicClient:
    """Anthropic API client implementation.
    
    Attributes:
        model: Model identifier
        api_key: Anthropic API key
        timeout: Request timeout in seconds
        client: Anthropic client instance
    """
    
    def __init__(self, model: str, api_key: str | None, timeout: int = 30):
        """Initialize Anthropic client.
        
        Args:
            model: Model identifier (e.g., claude-3-5-sonnet-20241022)
            api_key: Anthropic API key
            timeout: Request timeout in seconds
            
        Raises:
            AuthenticationError: If API key is missing
        """
        if not api_key:
            raise AuthenticationError("Anthropic API key is required")
        
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        except ImportError:
            raise LLMError(
                "anthropic package not installed. Install with: pip install anthropic"
            )
    
    def generate(self, prompt: str) -> str:
        """Generate text using Anthropic API.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails
        """
        try:
            import anthropic
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except anthropic.RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {e}") from e
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(f"Invalid Anthropic API key: {e}") from e
        except anthropic.APITimeoutError as e:
            raise TimeoutError(f"Anthropic request timed out: {e}") from e
        except Exception as e:
            raise LLMError(f"Anthropic API error: {e}") from e


class OpenAIClient:
    """OpenAI API client implementation.
    
    Attributes:
        model: Model identifier
        api_key: OpenAI API key
        timeout: Request timeout in seconds
        client: OpenAI client instance
    """
    
    def __init__(self, model: str, api_key: str | None, timeout: int = 30):
        """Initialize OpenAI client.
        
        Args:
            model: Model identifier (e.g., gpt-4)
            api_key: OpenAI API key
            timeout: Request timeout in seconds
            
        Raises:
            AuthenticationError: If API key is missing
        """
        if not api_key:
            raise AuthenticationError("OpenAI API key is required")
        
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key, timeout=timeout)
        except ImportError:
            raise LLMError(
                "openai package not installed. Install with: pip install openai"
            )
    
    def generate(self, prompt: str) -> str:
        """Generate text using OpenAI API.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails
        """
        try:
            import openai
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.choices[0].message.content
            
        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {e}") from e
        except openai.AuthenticationError as e:
            raise AuthenticationError(f"Invalid OpenAI API key: {e}") from e
        except openai.APITimeoutError as e:
            raise TimeoutError(f"OpenAI request timed out: {e}") from e
        except Exception as e:
            raise LLMError(f"OpenAI API error: {e}") from e


class OllamaClient:
    """Ollama API client implementation.
    
    Attributes:
        model: Model identifier
        base_url: Ollama API base URL
        timeout: Request timeout in seconds
    """
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 30):
        """Initialize Ollama client.
        
        Args:
            model: Model identifier (e.g., llama2)
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def generate(self, prompt: str) -> str:
        """Generate text using Ollama API.
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If generation fails
        """
        try:
            import requests
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("response", "")
            
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Ollama request timed out: {e}") from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Ollama rate limit exceeded: {e}") from e
            elif e.response.status_code in (401, 403):
                raise AuthenticationError(f"Ollama authentication failed: {e}") from e
            else:
                raise LLMError(f"Ollama HTTP error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Ollama request error: {e}") from e
        except ImportError:
            raise LLMError(
                "requests package not installed. Install with: pip install requests"
            )
        except Exception as e:
            raise LLMError(f"Ollama API error: {e}") from e
