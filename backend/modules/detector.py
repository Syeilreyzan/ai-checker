import math
import re
from typing import Any, Dict, List
from .llm_client import LLMClient
from .corrector import generate_fallback_suggestions

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
    "in conclusion",
    "ultimately",
    "leverage",
    "leveraging",
]


def split_sentences(text: str) -> List[str]:
    """Split text into clean sentences while preserving punctuation."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", cleaned)
    return [p.strip() for p in parts if p.strip()]


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
        # Humans have higher coefficient of variation (~0.45-0.85); AI is very uniform (~0.15-0.30)
        burstiness_score = min(100, int(round(cv * 140)))
    else:
        burstiness_score = 45

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


def _heuristic_sentence_analysis(idx: int, sentence: str) -> Dict[str, Any]:
    """Deterministic fallback scorer when no external LLM key is provided."""
    lower = sentence.lower()
    words = re.findall(r"\b\w+\b", sentence)
    word_count = len(words)

    matched_cliches = [c for c in AI_CLICHES if c in lower]
    reasons: List[str] = []
    score = 22

    if matched_cliches:
        score += min(55, len(matched_cliches) * 26)
        reasons.append(
            f"Contains signature AI phraseology ({', '.join(repr(c) for c in matched_cliches[:3])})"
        )

    if re.match(r"^(Furthermore|Moreover|Additionally|Consequently|Ultimately|In conclusion)\b", sentence):
        score += 24
        reasons.append("Starts with formal conjunctive adverb typical of LLM transitions")

    if 16 <= word_count <= 28 and "," in sentence and not re.search(r"['—!?\d%]", sentence):
        score += 18
        reasons.append("Balanced, uniform clause cadence with zero colloquial markers or specifics")

    # Human indicators reduce AI probability
    if re.search(r"\b(honestly|weird|nasty|annoying|let's|we're|didn't|don't|folks|quick)\b", lower):
        score -= 30
    if re.search(r"\b(\d+%|\d+am|\d+pm|v\d+\.\d+|q[1-4])\b", lower):
        score -= 22

    score = max(5, min(98, score))
    if score >= 65:
        status = "ai"
        if not reasons:
            reasons.append("Predictable token choices and synthetic corporate phrasing")
    elif score >= 40:
        status = "mixed"
        if not reasons:
            reasons.append("Partially polished structure resembling AI-assisted editing")
    else:
        status = "human"
        reasons = ["Natural human cadence, specific concrete details, and varied rhythm"]

    suggestions = (
        generate_fallback_suggestions(sentence) if status in ("ai", "mixed") else []
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
    Main AI Detection + Sentence Suggestion pipeline.
    Uses External LLM API when configured, with seamless fallback if no API key is present.
    """
    sentences = split_sentences(text)
    metrics = compute_linguistic_metrics(sentences)

    if not sentences:
        return {
            "overall_ai_probability": 0,
            "overall_human_probability": 100,
            "verdict": "Empty Text",
            "summary": "Please enter text to analyze.",
            "provider_used": llm_client.provider,
            "model_used": llm_client.model,
            "is_live_llm": llm_client.is_configured,
            "metrics": metrics,
            "sentences": [],
        }

    # Try external LLM analysis if API key is configured
    if llm_client.is_configured:
        try:
            numbered_sentences = [
                {"id": idx, "text": s} for idx, s in enumerate(sentences)
            ]
            system_prompt = (
                "You are an expert forensic linguist and AI text detector + humanizer editor. "
                "Analyze the given list of sentences for AI-generated patterns (ChatGPT, Claude, Gemini) "
                "such as low burstiness, overused transitions ('Furthermore', 'Moreover', 'delve', 'tapestry', "
                "'testament', 'strategic imperative'), robotic symmetry, and vague corporate abstractions.\n\n"
                "Return a JSON object with this exact schema:\n"
                "{\n"
                '  "overall_ai_probability": <int 0-100>,\n'
                '  "verdict": "<Likely AI-Generated | Mixed AI & Human | Authentic Human Writing>",\n'
                '  "summary": "<1-2 sentence executive explanation of why this text looks AI or human>",\n'
                '  "sentences": [\n'
                "    {\n"
                '      "id": <int matching input id>,\n'
                '      "ai_probability": <int 0-100>,\n'
                '      "status": "<ai | mixed | human>",  // "ai" if >=65, "mixed" if 40-64, "human" if <40\n'
                '      "reasons": ["<specific reason 1>", "<specific reason 2>"],\n'
                '      "suggestions": [\n'
                "        // Provide 3 distinct human-sounding rewrites ONLY if status is 'ai' or 'mixed' (empty list if 'human'):\n"
                '        {"label": "Natural & Direct", "tone": "natural", "text": "<authentic human rewrite>"},\n'
                '        {"label": "Executive Crisp", "tone": "executive", "text": "<sharp, specific business rewrite>"},\n'
                '        {"label": "Conversational", "tone": "casual", "text": "<warm, grounded human rewrite>"}\n'
                "      ]\n"
                "    }\n"
                "  ]\n"
                "}"
            )
            user_prompt = f"Analyze these sentences:\n{numbered_sentences}"
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
                    status = item.get("status")
                    if status not in ("ai", "mixed", "human"):
                        status = "ai" if prob >= 65 else ("mixed" if prob >= 40 else "human")
                    suggestions = item.get("suggestions") or []
                    if status in ("ai", "mixed") and not suggestions:
                        suggestions = generate_fallback_suggestions(sent_text)
                    enriched_sentences.append(
                        {
                            "id": idx,
                            "text": sent_text,
                            "original_text": sent_text,
                            "ai_probability": prob,
                            "status": status,
                            "reasons": item.get("reasons")
                            or ["Evaluated by linguistic detection model"],
                            "suggestions": suggestions,
                            "accepted": False,
                        }
                    )
                else:
                    enriched_sentences.append(_heuristic_sentence_analysis(idx, sent_text))

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
            return {
                "overall_ai_probability": overall_ai,
                "overall_human_probability": 100 - overall_ai,
                "verdict": llm_result.get("verdict")
                or _verdict_from_score(overall_ai),
                "summary": llm_result.get("summary")
                or "Analyzed via External LLM Forensic Engine.",
                "provider_used": llm_client.provider,
                "model_used": llm_client.model,
                "is_live_llm": True,
                "metrics": metrics,
                "sentences": enriched_sentences,
            }
        except Exception as exc:
            fallback_note = f"LLM API call failed ({str(exc)[:80]}); using built-in forensic analyzer."
    else:
        fallback_note = "Running built-in linguistic analyzer (Add API key in .env or Settings for live LLM deep inspection)."

    # Fallback deterministic analysis
    analyzed_sentences = [
        _heuristic_sentence_analysis(i, s) for i, s in enumerate(sentences)
    ]
    overall_ai = int(
        round(
            sum(s["ai_probability"] for s in analyzed_sentences)
            / len(analyzed_sentences)
        )
    )
    return {
        "overall_ai_probability": overall_ai,
        "overall_human_probability": 100 - overall_ai,
        "verdict": _verdict_from_score(overall_ai),
        "summary": fallback_note,
        "provider_used": llm_client.provider,
        "model_used": llm_client.model,
        "is_live_llm": False,
        "metrics": metrics,
        "sentences": analyzed_sentences,
    }


def _verdict_from_score(score: int) -> str:
    if score >= 65:
        return "Likely AI-Generated"
    if score >= 40:
        return "Mixed AI & Human"
    return "Authentic Human Writing"
