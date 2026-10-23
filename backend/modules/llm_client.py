import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import httpx

try:
    import google.generativeai as genai
except ImportError:
    genai = None


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
    """Unified async LLM client supporting OpenAI, Gemini Pro, and Anthropic."""

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
    def _clean_model_for_provider(prov: str, model: Optional[str], default: str) -> str:
        if not model or not model.strip():
            return default
        m = model.strip()
        if prov == "openai" and m.startswith(("gemini", "claude")):
            return default
        if prov == "gemini" and m.startswith(("gpt-", "o1", "o3", "claude")):
            return default
        if prov == "anthropic" and m.startswith(("gpt-", "gemini")):
            return default
        return m

    @classmethod
    def _resolve_credentials(
        cls, provider: Optional[str], api_key: Optional[str], model: Optional[str]
    ):
        default_models = {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            "gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-pro").strip() or "gemini-2.5-pro",
            "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip() or "claude-3-5-haiku-latest",
        }

        # 1. Explicit runtime API key override from UI
        if api_key and api_key.strip():
            prov = (provider or "openai").lower().strip()
            resolved_model = cls._clean_model_for_provider(
                prov, model, default_models.get(prov, "gpt-4o-mini")
            )
            return prov, api_key.strip(), resolved_model

        # 2. Check environment variables
        env_provider = (provider or os.getenv("LLM_PROVIDER", "")).lower().strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        if env_provider == "openai":
            return (
                "openai",
                openai_key,
                cls._clean_model_for_provider("openai", model, default_models["openai"]),
            )
        if env_provider == "gemini":
            return (
                "gemini",
                gemini_key,
                cls._clean_model_for_provider("gemini", model, default_models["gemini"]),
            )
        if env_provider == "anthropic":
            return (
                "anthropic",
                anthropic_key,
                cls._clean_model_for_provider("anthropic", model, default_models["anthropic"]),
            )

        # Auto-detect whichever key is configured in .env
        if openai_key:
            return (
                "openai",
                openai_key,
                cls._clean_model_for_provider("openai", model, default_models["openai"]),
            )
        if gemini_key:
            return (
                "gemini",
                gemini_key,
                cls._clean_model_for_provider("gemini", model, default_models["gemini"]),
            )
        if anthropic_key:
            return (
                "anthropic",
                anthropic_key,
                cls._clean_model_for_provider("anthropic", model, default_models["anthropic"]),
            )

        return "forensic_nlp", "", "forensic-linguistic-v2"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.provider in ("openai", "gemini", "anthropic"))

    async def _call_openai(
        self, api_key: str, model_name: str, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        if not api_key:
            raise RuntimeError("OpenAI API key is empty. Set OPENAI_API_KEY in .env or in the UI modal.")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.5,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            if resp.status_code != 200:
                try:
                    err_json = resp.json()
                    err_msg = err_json.get("error", {}).get("message") or resp.text[:200]
                except Exception:
                    err_msg = resp.text[:200]
                full_err = f"OpenAI API Error (HTTP {resp.status_code}): {err_msg}"
                print(f"[LLM ERROR] {full_err}", flush=True)
                raise RuntimeError(full_err)

            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return self._parse_json(raw_text)

    async def complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Request a structured JSON response from the active LLM provider."""
        if not self.is_configured:
            raise RuntimeError(
                f"No API key configured for provider '{self.provider.upper()}'. Please check .env or the API Config modal."
            )

        if self.provider == "openai":
            return await self._call_openai(
                self.api_key, self.model, system_prompt, user_prompt
            )

        if self.provider == "gemini":
            return await self._call_gemini(system_prompt, user_prompt)

        if self.provider == "anthropic":
            async with httpx.AsyncClient(timeout=60.0) as client:
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
                        "temperature": 0.4,
                        "system": system_prompt + "\nRespond ONLY with valid JSON.",
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                if resp.status_code != 200:
                    full_err = f"Anthropic API Error (HTTP {resp.status_code}): {resp.text[:200]}"
                    print(f"[LLM ERROR] {full_err}", flush=True)
                    raise RuntimeError(full_err)
                data = resp.json()
                raw_text = data["content"][0]["text"]
                return self._parse_json(raw_text)

        raise ValueError(f"Unsupported provider: {self.provider}")

    def _call_genai_sdk_sync(
        self, model_name: str, system_prompt: str, user_prompt: str
    ) -> str:
        """Synchronous helper using official google-generativeai SDK."""
        genai.configure(api_key=self.api_key)
        gen_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config={
                "temperature": 0.4,
                "response_mime_type": "application/json",
            },
        )
        response = gen_model.generate_content(user_prompt)
        return response.text

    async def _call_gemini(
        self, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        """Calls Google Gemini using official google-generativeai SDK with REST fallback."""
        if not self.api_key:
            raise RuntimeError("Gemini API key is empty. Set GEMINI_API_KEY in .env or in the UI modal.")

        candidate_models: List[str] = []
        for m in [
            self.model,
            "gemini-2.5-pro",
            "gemini-1.5-pro",
            "gemini-pro-latest",
            "gemini-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]:
            if m and m not in candidate_models:
                candidate_models.append(m)

        last_error = None

        if genai is not None and not self.api_key.startswith("AQ."):
            for model_name in candidate_models:
                try:
                    raw_text = await asyncio.to_thread(
                        self._call_genai_sdk_sync,
                        model_name,
                        system_prompt,
                        user_prompt,
                    )
                    if raw_text:
                        self.model = model_name
                        return self._parse_json(raw_text)
                except Exception as exc:
                    last_error = f"{model_name}: {str(exc)[:200]}"

        payload_with_sys = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json",
            },
        }

        is_vertex_key = self.api_key.startswith("AQ.")
        async with httpx.AsyncClient(timeout=60.0) as client:
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
                            try:
                                err_msg = resp.json().get("error", {}).get("message") or resp.text[:160]
                            except Exception:
                                err_msg = resp.text[:160]
                            last_error = f"HTTP {resp.status_code} ({model_name}): {err_msg}"
                    except Exception as exc:
                        last_error = str(exc)

        full_err = f"Gemini API Error ({last_error})"
        print(f"[LLM ERROR] {full_err}", flush=True)
        raise RuntimeError(full_err)

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
