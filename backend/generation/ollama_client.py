"""
NEXUS Local LLM Client
Modular interface for interacting with local Ollama daemon hosting qwen2.5:1.5b.
Provides offline-first, low-resource CPU-optimized inference and deterministic mock fallback.
"""

import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Optional, Iterator, Dict, Any, Generator
from backend.config import settings

logger = logging.getLogger("nexus.ollama_client")


class LLMError(Exception):
    """Base exception for LLM inference errors."""
    pass


class LLMConnectionError(LLMError):
    """Raised when the local Ollama daemon cannot be reached."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM response generation times out."""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for language model inference providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a complete text response given a prompt and optional system instructions."""
        pass

    @abstractmethod
    def stream_generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Stream response tokens as they are produced."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend model service is reachable and operational."""
        pass


class OllamaClient(BaseLLMClient):
    """
    Client for local Ollama server running qwen2.5:1.5b.
    Optimized for low-resource CPU inference with constrained context and temperature.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = (base_url or settings.models.ollama_base_url).rstrip("/")
        self.model = model or settings.models.llm_model
        self.temperature = temperature if temperature is not None else settings.models.llm_temperature
        self.max_tokens = min(max_tokens or settings.models.llm_max_tokens, 384)
        self.timeout = timeout or min(settings.models.llm_timeout_seconds, 25)

    def is_available(self) -> bool:
        """Check whether Ollama daemon is reachable and has the requested model."""
        endpoint = f"{self.base_url}/api/tags"
        try:
            resp = requests.get(endpoint, timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                # Match full tag (e.g. 'qwen2.5:1.5b') or base name ('qwen2.5:1.5b:latest')
                for m in models:
                    if self.model in m or m.startswith(self.model):
                        return True
                logger.warning("Ollama daemon is running, but model '%s' was not found in %s", self.model, models)
                return False
            return False
        except Exception as exc:
            logger.debug("Ollama availability check failed: %s", exc)
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Execute non-streaming inference against local Ollama endpoint.
        """
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": 1536,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                raise LLMError(f"Ollama server returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            return data.get("response", "").strip()

        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"Ollama generation timed out after {self.timeout}s: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMConnectionError(
                f"Failed to connect to local Ollama daemon at {self.base_url}. Ensure 'ollama serve' is running: {exc}"
            ) from exc
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"Ollama generation failed: {exc}") from exc

    def stream_generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Stream response tokens from Ollama generate endpoint.
        """
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": 2048,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with requests.post(endpoint, json=payload, stream=True, timeout=self.timeout) as resp:
                if resp.status_code != 200:
                    raise LLMError(f"Ollama streaming returned HTTP {resp.status_code}: {resp.text}")

                for line in resp.iter_lines():
                    if line:
                        chunk_data = json.loads(line.decode("utf-8"))
                        token = chunk_data.get("response", "")
                        if token:
                            yield token
                        if chunk_data.get("done", False):
                            break

        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"Ollama stream timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMConnectionError(f"Cannot reach Ollama stream: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"Streaming error: {exc}") from exc


class MockLLMClient(BaseLLMClient):
    """
    Deterministic mock LLM client for air-gapped unit testing and CI pipelines.
    Guarantees predictable provenance citations and simulated responses without GPU/CPU overhead.
    """

    def __init__(self, fixed_response: Optional[str] = None):
        self.fixed_response = fixed_response
        self._available = True

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_response(self, response: str) -> None:
        self.fixed_response = response

    def is_available(self) -> bool:
        return self._available

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self._available:
            raise LLMConnectionError("Mock LLM client set to unavailable.")

        if self.fixed_response is not None:
            return self.fixed_response

        # Check if evidence passages are present in prompt
        if "[REF-1]" in prompt:
            return (
                "Based on verified technical documentation [REF-1], the system must follow "
                "standard operational safety guidelines. Regular inspections and proper protocol "
                "ensure compliance and safe operation [REF-1]."
            )
        else:
            return "The authorized repository does not contain sufficient verified information to answer this inquiry."

    def stream_generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        response = self.generate(prompt, system_prompt)
        tokens = response.split(" ")
        for i, token in enumerate(tokens):
            if i < len(tokens) - 1:
                yield token + " "
            else:
                yield token
