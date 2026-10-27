"""
NEXUS Generation Package
Exposes local LLM client, Grounded RAG engine, and prompt engineering utilities.
"""

from backend.generation.ollama_client import (
    BaseLLMClient,
    OllamaClient,
    MockLLMClient,
    LLMError,
    LLMConnectionError,
    LLMTimeoutError
)
from backend.generation.rag_engine import (
    RAGEngine,
    NEXUS_SYSTEM_PROMPT,
    ABSTENTION_MESSAGE,
    get_default_rag_engine
)

__all__ = [
    "BaseLLMClient",
    "OllamaClient",
    "MockLLMClient",
    "LLMError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "RAGEngine",
    "NEXUS_SYSTEM_PROMPT",
    "ABSTENTION_MESSAGE",
    "get_default_rag_engine"
]
