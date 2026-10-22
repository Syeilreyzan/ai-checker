import json
import os
import re
from typing import Any, Dict, Optional
import httpx


class LLMClient:
    """Unified async LLM client supporting OpenAI, Gemini, and Anthropic."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider, self.api_key, self.model = self._resolve_credentials(
            provider, api_key, model
        )

    @staticmethod
    def _resolve_credentials(
        provider: Optional[str], api_key: Optional[str], model: Optional[str]
    ):
        # 1. Explicit runtime override from UI headers / payload
        if api_key and api_key.strip():
            prov = (provider or "openai").lower().strip()
            default_models = {
                "openai": "gpt-4o-mini",
                "gemini": "gemini-2.0-flash",
                "anthropic": "claude-3-5-haiku-latest",
            }
            return prov, api_key.strip(), model or default_models.get(prov, "gpt-4o-mini")

        # 2. Check environment variables
        env_provider = os.getenv("LLM_PROVIDER", "").lower().strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        if env_provider == "gemini" and gemini_key:
            return "gemini", gemini_key, os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        if env_provider == "anthropic" and anthropic_key:
            return (
                "anthropic",
                anthropic_key,
                os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            )
        if env_provider == "openai" and openai_key:
            return "openai", openai_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Auto-detect whichever key is configured in .env
        if openai_key:
            return "openai", openai_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if gemini_key:
            return "gemini", gemini_key, os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        if anthropic_key:
            return (
                "anthropic",
                anthropic_key,
                os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            )

        return "heuristic_fallback", "", "local-linguistic-v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.provider in ("openai", "gemini", "anthropic"))

    async def complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Request a structured JSON response from the active LLM provider."""
        if not self.is_configured:
            raise RuntimeError("No external LLM API key configured.")

        async with httpx.AsyncClient(timeout=45.0) as client:
            if self.provider == "openai":
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.3,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"]
                return self._parse_json(raw_text)

            elif self.provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
                resp = await client.post(
                    url,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": user_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "responseMimeType": "application/json",
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_json(raw_text)

            elif self.provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 4096,
                        "temperature": 0.3,
                        "system": system_prompt + "\nRespond ONLY with valid JSON.",
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["content"][0]["text"]
                return self._parse_json(raw_text)

        raise ValueError(f"Unsupported provider: {self.provider}")

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)
