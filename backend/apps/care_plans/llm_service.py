"""
LLM service for generating care plans.
Supports Claude (Anthropic) and OpenAI.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standard response from any LLM provider."""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    generation_time_ms: int


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate text from the LLM."""
        pass


class ClaudeLLMService(BaseLLMService):
    """Claude (Anthropic) LLM implementation."""
    
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
    
    def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate text using Claude."""
        start_time = time.time()
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt or "",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return LLMResponse(
            content=message.content[0].text,
            model=message.model,
            prompt_tokens=message.usage.input_tokens,
            completion_tokens=message.usage.output_tokens,
            total_tokens=message.usage.input_tokens + message.usage.output_tokens,
            generation_time_ms=generation_time,
        )


class OpenAILLMService(BaseLLMService):
    """OpenAI GPT LLM implementation."""
    
    def __init__(self):
        import openai
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
    
    def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Generate text using OpenAI."""
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=messages,
        )
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            generation_time_ms=generation_time,
        )


class MockLLMService(BaseLLMService):
    """Mock LLM service for testing."""
    
    def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        """Return mock response."""
        return LLMResponse(
            content="# Mock Care Plan\n\nThis is a mock care plan for testing.\n\n## Problems\n- Test problem\n\n## Goals\n- Test goal\n\n## Interventions\n- Test intervention",
            model="mock-model",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            generation_time_ms=100,
        )


def get_llm_service() -> BaseLLMService:
    """Factory function to get the appropriate LLM service."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "claude":
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("No Anthropic API key, using mock service")
            return MockLLMService()
        return ClaudeLLMService()
    
    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            logger.warning("No OpenAI API key, using mock service")
            return MockLLMService()
        return OpenAILLMService()
    
    elif provider == "mock":
        return MockLLMService()
    
    else:
        logger.warning(f"Unknown LLM provider '{provider}', using mock service")
        return MockLLMService()
