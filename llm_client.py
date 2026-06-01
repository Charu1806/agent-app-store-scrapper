"""Shared LLM client factory for analyzer, gap_finder, and agent orchestration."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional


def parse_json_response(text: str) -> Dict[str, Any]:
    """Extract JSON from an LLM response that may include markdown fences."""
    if not text or not text.strip():
        raise ValueError("Empty LLM response")
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise ValueError(f"Could not parse JSON: {text[:200]}...")


def create_llm_client(provider: Optional[str] = None):
    """Return a client with .complete(system, user) -> str for the given provider."""
    name = (provider or os.getenv("LLM_PROVIDER", "gemini")).strip().lower()

    if name == "gemini":
        from google import genai
        from google.genai import types

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY required for gemini")
        client = genai.Client(api_key=key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

        class Client:
            def complete(self, system: str, user: str) -> str:
                response = client.models.generate_content(
                    model=model,
                    contents=user,
                    config=types.GenerateContentConfig(system_instruction=system),
                )
                return response.text or ""

        return Client()

    if name == "groq":
        from groq import Groq

        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY required for groq")
        c = Groq(api_key=key)
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        class Client:
            def complete(self, system: str, user: str) -> str:
                r = c.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.2,
                )
                return r.choices[0].message.content or ""

        return Client()

    if name == "mistral":
        from mistralai import Mistral

        key = os.getenv("MISTRAL_API_KEY")
        if not key:
            raise ValueError("MISTRAL_API_KEY required for mistral")
        c = Mistral(api_key=key)
        model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

        class Client:
            def complete(self, system: str, user: str) -> str:
                r = c.chat.complete(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                )
                return r.choices[0].message.content or ""

        return Client()

    if name == "huggingface":
        from huggingface_hub import InferenceClient

        token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
        if not token:
            raise ValueError("HUGGINGFACE_API_KEY required for huggingface")
        model = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
        c = InferenceClient(model=model, token=token)

        class Client:
            def complete(self, system: str, user: str) -> str:
                r = c.chat_completion(
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=4096,
                )
                return r.choices[0].message.content or ""

        return Client()

    if name == "ollama":
        import requests

        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")

        class Client:
            def complete(self, system: str, user: str) -> str:
                r = requests.post(
                    f"{base}/api/chat",
                    json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "stream": False},
                    timeout=120,
                )
                r.raise_for_status()
                return r.json().get("message", {}).get("content", "")

        return Client()

    if name == "claude":
        import anthropic

        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY required for claude")
        c = anthropic.Anthropic(api_key=key)
        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        class Client:
            def complete(self, system: str, user: str) -> str:
                r = c.messages.create(model=model, max_tokens=4096, system=system, messages=[{"role": "user", "content": user}])
                return "\n".join(b.text for b in r.content if hasattr(b, "text") and b.text)

        return Client()

    raise ValueError(f"Unsupported LLM_PROVIDER: {name}. Use gemini|groq|mistral|huggingface|ollama|claude")
