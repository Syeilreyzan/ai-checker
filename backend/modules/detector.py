import json
import math
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from .llm_client import LLMClient
from .corrector import generate_fallback_suggestions, call_tohuman_api

AI_CLICHES = [
    "delve",
    "delving",
    "tapestry",
    "testament",
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "paradigm shift",
    "cutting-edge",
    "rapidly evolving",
    "digital landscape",
    "strategic imperative",
    "unwavering",
    "foster a culture",
    "holistic approach",
    "paving the way",
    "unlock unprecedented",
    "seamlessly",
    "orchestrate",
    "precipice",
    "transformative journey",
    "not merely",
    "it is crucial",
    "it is essential",
    "it is important to note",
    "it is worth noting",
    "in conclusion",
    "ultimately",
    "leverage",
    "leveraging",
    "utilize",
    "utilizing",
    "plays a crucial role",
    "plays a vital role",
    "plays a pivotal role",
    "plays a key role",
    "underscores the importance",
    "highlights the importance",
    "in today's fast-paced",
    "in today's world",
    "comprehensive overview",
    "robust framework",
    "key takeaway",
    "significant impact",
    "continuous innovation",
    "operational efficiencies",
    "operational efficiency",
    "operational overhead",
    "actionable insights",
    "vast datasets",
    "repetitive tasks",
    "daily workflows",
    "competitive market",
    "technological advancements",
]

AI_STRUCTURAL_PATTERNS = [
    (
        r"\b(in order to|by leveraging|by utilizing|by implementing|by integrating|by adopting|by fostering|by automating|by focusing)\b",
        "Formulaic participial or purpose clause typical of Gemini/ChatGPT output",
    ),
    (
        r"\b(allows for|enables organizations|empowering teams|ensures that|serves as a|acts as a|transforming the way|redefining how|positioned to)\b",
        "Impersonal corporate verb construction common in LLM prose",
    ),
    (
        r"\b(crucial|pivotal|paramount|indispensable|imperative|unprecedented|transformative|holistic|seamless|robust|comprehensive|actionable|significantly|increasingly|effectively)\b",
        "High-frequency LLM intensifier or corporate qualifier",
    ),
    (
        r"\b(not only .* but also|whether .* or .*|while reducing|while maintaining|while ensuring)\b",
        "Symmetrical rhetorical framing characteristic of AI models",
    ),
    (
        r"\b(organizations|individuals|stakeholders|methodologies|capabilities|functionalities|initiatives|advancements|implementation|optimization)\b",
        "Formal institutional vocabulary favored by LLM token predictors",
    ),
]


def split_sentences(text: str) -> List[str]:
    """Split text into clean sentences across paragraphs and punctuation."""
    if not text or not text.strip():
        return []
    paragraphs = [p.strip() for p in re.split(r"\n+", text.strip()) if p.strip()]
    sentences: List[str] = []
    for para in paragraphs:
        cleaned = re.sub(r"\s+", " ", para)
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘(\[])", cleaned)
        for p in parts:
            s = p.strip()
            if s:
                sentences.append(s)
    return sentences


def compute_linguistic_metrics(sentences: List[str]) -> Dict[str, Any]:
    """Calculate quantitative linguistic signals: burstiness, vocabulary richness, and cliché count."""
    if not sentences:
        return {
            "burstiness_score": 0,
            "vocabulary_richness": 0,
            "uniformity_score": 0,
            "cliche_count": 0,
            "word_count": 0,
            "sentence_count": 0,
        }

    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    total_words = sum(lengths)
    mean_len = total_words / len(lengths) if lengths else 1.0

    if len(lengths) > 1:
        variance = sum((x - mean_len) ** 2 for x in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_len if mean_len > 0 else 0
        burstiness_score = min(100, int(round(cv * 140)))
    else:
        burstiness_score = 40

    all_words = [w.lower() for s in sentences for w in re.findall(r"\b[a-zA-Z']+\b", s)]
    unique_words = set(all_words)
    ttr = (len(unique_words) / len(all_words)) if all_words else 0.0
    vocabulary_richness = min(100, int(round(ttr * 125)))

    full_lower = " ".join(sentences).lower()
    cliche_hits = [c for c in AI_CLICHES if c in full_lower]
    uniformity_score = max(0, 100 - burstiness_score)

    return {
        "burstiness_score": burstiness_score,
        "vocabulary_richness": vocabulary_richness,
        "uniformity_score": uniformity_score,
        "cliche_count": len(cliche_hits),
        "detected_cliches": cliche_hits[:8],
        "word_count": total_words,
        "sentence_count": len(sentences),
    }


def compute_quota_metrics(sentences: List[Dict[str, Any]], total_words: int) -> Dict[str, Any]:
    """
    Calculates how much of ToHuman's 2,500 free monthly words are saved by using
    Stage 1 Detection Screening first and only sending flagged sentences for humanization.
    """
    flagged_words = sum(
        len(re.findall(r"\b\w+\b", s["original_text"]))
        for s in sentences
        if s.get("status") in ("ai", "mixed")
    )
    skipped_human_words = max(0, total_words - flagged_words)
    saved_pct = (
        int(round((skipped_human_words / total_words) * 100))
        if total_words > 0
        else 0
    )
    return {
        "total_words": total_words,
        "targeted_flagged_words": flagged_words,
        "skipped_human_words": skipped_human_words,
        "quota_saved_percent": saved_pct,
        "tohuman_monthly_free_limit": 2500,
    }


async def call_sapling_detector(text: str, sapling_key: str) -> Optional[Dict[str, Any]]:
    """
    Stage 1 Free Detection Option A: Sapling AI Detector API (https://api.sapling.ai/api/v1/aidetect)
    Returns overall score and native sentence_scores.
    """
    if not sapling_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.sapling.ai/api/v1/aidetect",
                json={"key": sapling_key, "text": text, "sent_scores": True},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        print(f"[SAPLING API NOTICE] {exc}", flush=True)
    return None


async def call_huggingface_detector(
    sentences: List[str], hf_key: str
) -> Optional[List[int]]:
    """
    Stage 1 Free Detection Option B: Hugging Face Open-Source RoBERTa AI Detector
    (openai-community/roberta-base-openai-detector)
    """
    if not hf_key or not sentences:
        return None
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api-inference.huggingface.co/models/openai-community/roberta-base-openai-detector",
                headers={"Authorization": f"Bearer {hf_key}"},
                json={"inputs": sentences},
            )
            if resp.status_code == 200:
                data = resp.json()
                scores: List[int] = []
                for item in data:
                    if isinstance(item, list):
                        fake_prob = next(
                            (
                                x["score"]
                                for x in item
                                if x.get("label", "").lower() in ("fake", "label_0", "ai")
                            ),
                            0.5,
                        )
                        scores.append(int(round(fake_prob * 100)))
                if len(scores) == len(sentences):
                    return scores
    except Exception as exc:
        print(f"[HUGGINGFACE API NOTICE] {exc}", flush=True)
    return None


def _heuristic_sentence_analysis(
    idx: int, sentence: str, doc_uniformity: int = 50
) -> Dict[str, Any]:
    """Multi-signal forensic linguistic scorer for sentence-level AI detection."""
    lower = sentence.lower()
    words = re.findall(r"\b[a-zA-Z']+\b", sentence)
    word_count = len(words)

    matched_cliches = [c for c in AI_CLICHES if c in lower]
    reasons: List[str] = []
    score = 38

    if matched_cliches:
        score += min(52, len(matched_cliches) * 24)
        reasons.append(
            f"Contains signature AI phraseology ({', '.join(repr(c) for c in matched_cliches[:3])})"
        )

    for pattern, reason_desc in AI_STRUCTURAL_PATTERNS:
        if re.search(pattern, lower):
            score += 16
            if reason_desc not in reasons:
                reasons.append(reason_desc)

    if re.match(
        r"^(Furthermore|Moreover|Additionally|Consequently|Ultimately|In conclusion|Overall|Notably|Importantly|Therefore|Thus|However|Nevertheless|Nonetheless)\b",
        sentence,
    ):
        score += 20
        reasons.append("Starts with formal conjunctive transition typical of LLM output")

    if word_count >= 8:
        nominalizations = [
            w
            for w in words
            if len(w) >= 7
            and w.lower().endswith(
                ("tion", "tions", "ment", "ments", "ity", "ities", "ance", "ence", "iveness", "izing", "ating")
            )
        ]
        nom_ratio = len(nominalizations) / word_count
        if nom_ratio >= 0.12:
            score += 20
            reasons.append(
                f"High density of abstract Latinate nouns/participles ({', '.join(nominalizations[:3])})"
            )
        elif nom_ratio >= 0.06:
            score += 12

    avg_word_len = (sum(len(w) for w in words) / word_count) if word_count else 0
    has_contraction = bool(re.search(r"\b\w+'(t|re|ve|ll|m|d|s)\b", lower))
    if word_count >= 12 and avg_word_len >= 5.0 and not has_contraction:
        score += 18
        reasons.append("Low perplexity academic/corporate tone with zero natural contractions")

    if 13 <= word_count <= 34 and not re.search(r"[!?;—()]", sentence) and not has_contraction:
        score += 12
        if doc_uniformity >= 55:
            score += 10
            reasons.append("Uniform sentence length and symmetrical LLM cadence")

    if re.search(
        r"\b(honestly|weird|nasty|annoying|let's|we're|didn't|don't|can't|won't|isn't|that's|here's|folks|quick|heads-up|btw|imo|yeah|pretty|super|stuff|guys|trick|look)\b",
        lower,
    ):
        score -= 35
    if re.search(
        r"\b(\d+%|\d+am|\d+pm|v\d+\.\d+|q[1-4]|monday|tuesday|wednesday|thursday|friday)\b",
        lower,
    ):
        score -= 24
    if "—" in sentence or "?" in sentence or "!" in sentence:
        score -= 14

    score = max(6, min(98, score))
    if score >= 65:
        status = "ai"
        if not reasons:
            reasons.append("Predictable token probability and synthetic corporate phrasing")
    elif score >= 40:
        status = "mixed"
        if not reasons:
            reasons.append("Partially polished structure resembling AI-assisted editing")
    else:
        status = "human"
        reasons = ["Natural human cadence, specific concrete details, and varied rhythm"]

    suggestions = (
        generate_fallback_suggestions(sentence, idx_seed=idx)
        if status in ("ai", "mixed")
        else []
    )

    return {
        "id": idx,
        "text": sentence,
        "original_text": sentence,
        "ai_probability": score,
        "status": status,
        "reasons": reasons,
        "suggestions": suggestions,
        "accepted": False,
    }


async def analyze_text_with_modules(
    text: str, llm_client: LLMClient
) -> Dict[str, Any]:
    """
    Two-Stage AI Checker & Targeted Humanizer Architecture:
    - Stage 1 (Detection Screening): Sapling Free API / Hugging Face RoBERTa / Forensic + LLM
      identifies which sentences trigger AI alerts without wasting humanization quota.
    - Stage 2 (Targeted Humanization): Applies ToHuman (2,500 free words/mo) or LLM/Anti-Detector
      rewriting ONLY to the flagged AI sentences.
    """
    sentences = split_sentences(text)
    metrics = compute_linguistic_metrics(sentences)
    doc_uniformity = metrics.get("uniformity_score", 50)
    total_words = metrics.get("word_count", 0)

    if not sentences:
        return {
            "overall_ai_probability": 0,
            "overall_human_probability": 100,
            "verdict": "Empty Text",
            "summary": "Please enter text to analyze.",
            "provider_used": llm_client.provider,
            "model_used": llm_client.model,
            "detection_stage_engine": "Forensic Baseline",
            "humanizer_stage_engine": "Targeted Humanizer",
            "is_live_llm": llm_client.is_configured,
            "metrics": metrics,
            "quota_metrics": compute_quota_metrics([], 0),
            "sentences": [],
        }

    sapling_key = os.getenv("SAPLING_API_KEY", "").strip()
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    tohuman_key = os.getenv("TOHUMAN_API_KEY", "").strip()

    # Check if Sapling or Hugging Face free detection API is configured for Stage 1
    sapling_res = await call_sapling_detector(text, sapling_key) if sapling_key else None
    hf_scores = (
        await call_huggingface_detector(sentences, hf_key)
        if (hf_key and not sapling_res)
        else None
    )

    # Try external LLM analysis if API key is configured
    if llm_client.is_configured:
        try:
            numbered_sentences = [
                {"id": idx, "text": s} for idx, s in enumerate(sentences)
            ]
            system_prompt = (
                "You are an expert forensic AI detector and Anti-AI-Detector human ghostwriter. "
                "Analyze the given JSON list of sentences for AI-generated patterns (ChatGPT, Gemini, Claude) "
                "such as low perplexity, uniform sentence length (low burstiness), participial clauses ('By integrating...'), "
                "formal transitions ('Furthermore', 'Moreover', 'However', 'Ultimately'), and corporate nouns.\n\n"
                "CRITICAL HUMANIZATION RULES for your `suggestions`:\n"
                "Your rewrite suggestions MUST pass GPTZero, ZeroGPT, and QuillBot as 100% Human (0% AI). To do this:\n"
                "1. Inject extreme burstiness: split 20-word sentences into a short 3-6 word punchy sentence + a conversational sentence, or use em-dashes (—) and rhetorical questions.\n"
                "2. Always use natural contractions (it's, don't, we're, can't, won't, that's).\n"
                "3. Replace ALL LLM words (transforming, leveraging, utilizing, enhancing, organizations, workflows, actionable insights, operational, crucial, pivotal, comprehensive, seamless) with plain everyday words (use, fix, cut, build, teams, day-to-day work).\n\n"
                "Return ONLY a valid JSON object with this exact schema:\n"
                "{\n"
                '  "overall_ai_probability": <int 0-100>,\n'
                '  "verdict": "<Likely AI-Generated | Mixed AI & Human | Authentic Human Writing>",\n'
                '  "summary": "<1-2 sentence executive explanation of why this text looks AI or human>",\n'
                '  "sentences": [\n'
                "    {\n"
                '      "id": <int matching input id>,\n'
                '      "ai_probability": <int 0-100>,\n'
                '      "status": "<ai | mixed | human>",\n'
                '      "reasons": ["<specific reason 1>", "<specific reason 2>"],\n'
                '      "suggestions": [\n'
                '        {"label": "Natural & Direct (Anti-AI Detector)", "tone": "natural", "text": "<high-burstiness human rewrite 1>"},\n'
                '        {"label": "Executive Crisp", "tone": "executive", "text": "<sharp, specific human rewrite 2>"},\n'
                '        {"label": "Conversational & High-Burstiness", "tone": "casual", "text": "<warm, colloquial human rewrite 3>"}\n'
                "      ]\n"
                "    }\n"
                "  ]\n"
                "}"
            )
            user_prompt = (
                "Analyze these sentences and provide 3 high-burstiness, anti-AI-detector human rewrite suggestions for every sentence with status 'ai' or 'mixed':\n"
                + json.dumps(numbered_sentences, ensure_ascii=False)
            )
            llm_result = await llm_client.complete_json(system_prompt, user_prompt)

            llm_sentences_by_id = {
                int(item.get("id", i)): item
                for i, item in enumerate(llm_result.get("sentences", []))
            }

            enriched_sentences = []
            for idx, sent_text in enumerate(sentences):
                item = llm_sentences_by_id.get(idx)
                if item:
                    prob = max(0, min(100, int(item.get("ai_probability", 50))))
                    # Blend with Sapling or HuggingFace score if configured
                    if hf_scores and idx < len(hf_scores):
                        prob = int(round((prob + hf_scores[idx]) / 2))
                    status = item.get("status")
                    if status not in ("ai", "mixed", "human"):
                        status = "ai" if prob >= 65 else ("mixed" if prob >= 40 else "human")
                    suggestions = item.get("suggestions") or []
                    if status in ("ai", "mixed") and not suggestions:
                        suggestions = generate_fallback_suggestions(sent_text, idx_seed=idx)
                    enriched_sentences.append(
                        {
                            "id": idx,
                            "text": sent_text,
                            "original_text": sent_text,
                            "ai_probability": prob,
                            "status": status,
                            "reasons": item.get("reasons")
                            or ["Flagged during Stage 1 AI Detection Screening"],
                            "suggestions": suggestions,
                            "accepted": False,
                        }
                    )
                else:
                    enriched_sentences.append(
                        _heuristic_sentence_analysis(idx, sent_text, doc_uniformity)
                    )

            overall_ai = int(
                llm_result.get(
                    "overall_ai_probability",
                    round(
                        sum(s["ai_probability"] for s in enriched_sentences)
                        / len(enriched_sentences)
                    ),
                )
            )
            overall_ai = max(0, min(100, overall_ai))
            quota_metrics = compute_quota_metrics(enriched_sentences, total_words)
            return {
                "overall_ai_probability": overall_ai,
                "overall_human_probability": 100 - overall_ai,
                "verdict": llm_result.get("verdict")
                or _verdict_from_score(overall_ai),
                "summary": llm_result.get("summary")
                or f"Stage 1 Detection + Stage 2 Targeted Rewriting via {llm_client.provider.upper()} ({llm_client.model}).",
                "provider_used": llm_client.provider,
                "model_used": llm_client.model,
                "detection_stage_engine": (
                    "Sapling Free Detector + LLM"
                    if sapling_res
                    else ("HuggingFace RoBERTa + LLM" if hf_scores else f"{llm_client.provider.upper()} Screening")
                ),
                "humanizer_stage_engine": (
                    "ToHuman API (2,500 Free Words)"
                    if tohuman_key
                    else f"Targeted {llm_client.provider.upper()} Humanizer"
                ),
                "is_live_llm": True,
                "llm_error": None,
                "metrics": metrics,
                "quota_metrics": quota_metrics,
                "sentences": enriched_sentences,
            }
        except Exception as exc:
            llm_error_msg = str(exc)
    else:
        llm_error_msg = None

    # Fallback / Free Baseline Detection + Targeted Humanizer
    analyzed_sentences = []
    sapling_sents = (sapling_res or {}).get("sentence_scores", [])
    for i, s in enumerate(sentences):
        heur = _heuristic_sentence_analysis(i, s, doc_uniformity)
        if i < len(sapling_sents) and isinstance(sapling_sents[i], dict):
            sap_score = int(round(float(sapling_sents[i].get("score", 0.5)) * 100))
            heur["ai_probability"] = sap_score
            heur["status"] = "ai" if sap_score >= 65 else ("mixed" if sap_score >= 40 else "human")
        elif hf_scores and i < len(hf_scores):
            heur["ai_probability"] = hf_scores[i]
            heur["status"] = "ai" if hf_scores[i] >= 65 else ("mixed" if hf_scores[i] >= 40 else "human")

        # If ToHuman API is configured, call it ONLY on high-AI sentences to save the 2,500-word free quota!
        if tohuman_key and heur["status"] == "ai":
            th_rewrite = await call_tohuman_api(s, tohuman_key)
            if th_rewrite:
                heur["suggestions"].insert(
                    0,
                    {
                        "label": "ToHuman API (Targeted Rewrite)",
                        "tone": "tohuman",
                        "text": th_rewrite,
                    },
                )
        analyzed_sentences.append(heur)

    overall_ai = int(
        round(
            sum(s["ai_probability"] for s in analyzed_sentences)
            / len(analyzed_sentences)
        )
    )
    quota_metrics = compute_quota_metrics(analyzed_sentences, total_words)
    summary_text = (
        f"Stage 1 Screening evaluated {len(sentences)} sentences ({total_words} words) and isolated "
        f"{quota_metrics['targeted_flagged_words']} AI-flagged words—saving {quota_metrics['quota_saved_percent']}% of your humanization quota."
    )
    return {
        "overall_ai_probability": overall_ai,
        "overall_human_probability": 100 - overall_ai,
        "verdict": _verdict_from_score(overall_ai),
        "summary": summary_text,
        "provider_used": llm_client.provider,
        "model_used": llm_client.model,
        "detection_stage_engine": (
            "Sapling Free API"
            if sapling_res
            else ("HuggingFace Open-Source RoBERTa" if hf_scores else "Forensic Linguistic Baseline (Free)")
        ),
        "humanizer_stage_engine": (
            "ToHuman API (2,500 Free Words/mo)"
            if tohuman_key
            else "Targeted Anti-Detector Rewriter"
        ),
        "is_live_llm": bool(sapling_res or hf_scores or tohuman_key),
        "llm_error": llm_error_msg,
        "metrics": metrics,
        "quota_metrics": quota_metrics,
        "sentences": analyzed_sentences,
    }


def _verdict_from_score(score: int) -> str:
    if score >= 65:
        return "Likely AI-Generated"
    if score >= 40:
        return "Mixed AI & Human"
    return "Authentic Human Writing"
