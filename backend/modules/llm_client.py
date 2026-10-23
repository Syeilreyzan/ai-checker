import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import httpx


def _reload_env():
    """Reload .env on every request so changes to .env take effect without container rebuild."""
    backend_dir = Path(__file__).resolve().parent.parent
    root_env = backend_dir.parent / ".env"
    local_env = backend_dir / ".env"
    if local_env.exists():
        load_dotenv(local_env, override=True)
    if root_env.exists():
        load_dotenv(root_env, override=True)


class LLMClient:
    """Unified async LLM client supporting Gemini Pro (AI Studio & Vertex Express), OpenAI, and Anthropic."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        _reload_env()
        self.provider, self.api_key, self.model = self._resolve_credentials(
            provider, api_key, model
        )

    @staticmethod
    def _resolve_credentials(
        provider: Optional[str], api_key: Optional[str], model: Optional[str]
    ):
        default_models = {
            "gemini": "gemini-2.5-pro",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
        }

        # 1. Explicit runtime API key override from UI
        if api_key and api_key.strip():
            prov = (provider or "gemini").lower().strip()
            return (
                prov,
                api_key.strip(),
                (model or default_models.get(prov, "gemini-2.5-pro")).strip(),
            )

        # 2. Check environment variables (and respect runtime provider/model selection if provided)
        env_provider = (provider or os.getenv("LLM_PROVIDER", "")).lower().strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        if env_provider == "gemini" and gemini_key:
            resolved_model = (
                model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
            ).strip()
            return "gemini", gemini_key, resolved_model
        if env_provider == "anthropic" and anthropic_key:
            resolved_model = (
                model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
            ).strip()
            return "anthropic", anthropic_key, resolved_model
        if env_provider == "openai" and openai_key:
            resolved_model = (
                model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            ).strip()
            return "openai", openai_key, resolved_model

        # Auto-detect whichever key is configured in .env
        if gemini_key:
            return (
                "gemini",
                gemini_key,
                (model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")).strip(),
            )
        if openai_key:
            return (
                "openai",
                openai_key,
                (model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip(),
            )
        if anthropic_key:
            return (
                "anthropic",
                anthropic_key,
                (model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")).strip(),
            )

        return "forensic_nlp", "", "forensic-linguistic-v2"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.provider in ("openai", "gemini", "anthropic"))

    async def complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Request a structured JSON response from the active LLM provider."""
        if not self.is_configured:
            raise RuntimeError("No external LLM API key configured.")

        async with httpx.AsyncClient(timeout=60.0) as client:
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
                        "temperature": 0.2,
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
                return await self._call_gemini(client, system_prompt, user_prompt)

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
                        "temperature": 0.2,
                        "system": system_prompt + "\nRespond ONLY with valid JSON.",
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["content"][0]["text"]
                return self._parse_json(raw_text)

        raise ValueError(f"Unsupported provider: {self.provider}")

    async def _call_gemini(
        self, client: httpx.AsyncClient, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        """
        Calls Google Gemini Pro supporting both:
        1. Google AI Studio keys (AIza...) -> generativelanguage.googleapis.com
        2. Vertex AI Express Mode keys (AQ....) -> aiplatform.googleapis.com & generativelanguage.googleapis.com
        """
        candidate_models: List[str] = []
        for m in [
            self.model,
            "gemini-2.5-pro",
            "gemini-1.5-pro",
            "gemini-pro-latest",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]:
            if m and m not in candidate_models:
                candidate_models.append(m)

        payload_with_sys = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        is_vertex_key = self.api_key.startswith("AQ.")
        last_error = None

        for model_name in candidate_models:
            endpoints = (
                [
                    f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model_name}:generateContent",
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                ]
                if is_vertex_key
                else [
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                    f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model_name}:generateContent",
                ]
            )

            for url in endpoints:
                try:
                    resp = await client.post(
                        url,
                        params={"key": self.api_key},
                        headers={"Content-Type": "application/json"},
                        json=payload_with_sys,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        self.model = model_name
                        return self._parse_json(raw_text)
                    else:
                        last_error = f"HTTP {resp.status_code} ({model_name}): {resp.text[:160]}"
                except Exception as exc:
                    last_error = str(exc)

        raise RuntimeError(f"Gemini Pro API error ({last_error})")

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)
