from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules.llm_client import LLMClient
from modules.detector import analyze_text_with_modules
from modules.corrector import rewrite_flagged_sentence
from modules.samples import SAMPLES

# Load .env from project root or backend directory
root_env = Path(__file__).resolve().parent.parent / ".env"
local_env = Path(__file__).resolve().parent / ".env"
if root_env.exists():
    load_dotenv(root_env)
elif local_env.exists():
    load_dotenv(local_env)

app = FastAPI(
    title="VeriText AI — Detection & Humanizer Engine",
    description="Modular Python API for sentence-level AI origin detection and interactive humanization.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class CorrectSentenceRequest(BaseModel):
    sentence: str
    context_text: Optional[str] = ""
    tone: Optional[str] = "natural"
    custom_instruction: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class TestKeyRequest(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


@app.get("/api/health")
async def health_check():
    client = LLMClient()
    return {
        "status": "ok",
        "configured_provider": client.provider,
        "configured_model": client.model,
        "has_env_api_key": client.is_configured,
    }


@app.post("/api/test-key")
async def test_api_key(payload: TestKeyRequest):
    """Test whether the active or provided API key works with OpenAI / Gemini / Anthropic."""
    client = LLMClient(
        provider=payload.provider,
        api_key=payload.api_key,
        model=payload.model,
    )
    if not client.is_configured:
        return {
            "valid": False,
            "provider": client.provider,
            "model": client.model,
            "message": f"No API key found for provider '{client.provider.upper()}'. Paste a key in .env or in the modal.",
        }
    try:
        await client.complete_json(
            system_prompt="Return a JSON object with status ok.",
            user_prompt='Respond with {"status": "ok"}',
        )
        return {
            "valid": True,
            "provider": client.provider,
            "model": client.model,
            "message": f"Connected to {client.provider.upper()} ({client.model}) — API Key is valid!",
        }
    except Exception as exc:
        return {
            "valid": False,
            "provider": client.provider,
            "model": client.model,
            "message": str(exc),
        }


@app.get("/api/samples")
async def get_samples():
    return {"samples": SAMPLES}


@app.post("/api/analyze")
async def analyze_text(payload: AnalyzeRequest):
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    client = LLMClient(
        provider=payload.provider,
        api_key=payload.api_key,
        model=payload.model,
    )
    return await analyze_text_with_modules(payload.text, client)


@app.post("/api/correct-sentence")
async def correct_sentence(payload: CorrectSentenceRequest):
    if not payload.sentence or not payload.sentence.strip():
        raise HTTPException(status_code=400, detail="Sentence cannot be empty.")

    client = LLMClient(
        provider=payload.provider,
        api_key=payload.api_key,
        model=payload.model,
    )
    return await rewrite_flagged_sentence(
        sentence=payload.sentence,
        context_text=payload.context_text or "",
        tone=payload.tone or "natural",
        custom_instruction=payload.custom_instruction,
        llm_client=client,
    )
