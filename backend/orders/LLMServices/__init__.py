# adapters/__init__.py

from .mock import MockLLMAdapter
from .gemini import GeminiAdapter
from django.conf import settings

def get_LLM_adapter():
    """工厂函数：根据数据来源返回对应的 adapter"""
    provider = getattr(settings, "LLM_PROVIDER", "gemini")
    if provider == "gemini":
        return GeminiAdapter()
    elif provider == "mock":
        return MockLLMAdapter()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
