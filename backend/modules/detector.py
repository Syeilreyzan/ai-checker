import json
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
    "underscores the importance",
    "in today's fast-paced",
    "in today's world",
    "comprehensive overview",
    "robust framework",
    "key takeaway",
    "significant impact",
    "continuous innovation",
    "operational efficiencies",
]

AI_STRUCTURAL_PATTERNS = [
    (r"\b(in order to|by leveraging|by utilizing|by implementing|by adopting|by fostering)\b", "Formulaic participial or purpose clause typical of LLM generation"),
    (r"\b(allows for|enables organizations|empowering teams|ensures that|serves as a|acts as a)\b", "Impersonal corporate verb construction common in AI prose"),
    (r"\b(crucial|pivotal|paramount|indispensable|imperative|unprecedented|transformative|holistic|seamless|robust|comprehensive)\b", "High-frequency LLM intensifier adjective"),
    (r"\b(not only .* but also|whether .* or .*|from .* to .*)\b", "Symmetrical rhetorical framing characteristic of AI models"),
]


def split_sentences(text: str) -> List[str]:
    """Split text into clean sentences across paragraphs and punctuation."""
    if not text or not text.strip():
        return []
    # Split on newlines first so multi-paragraph pastes segment cleanly
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


def _heuristic_sentence_analysis(
    idx: int, sentence: str, doc_uniformity: int = 50
) -> Dict[str, Any]:
    """Multi-signal forensic linguistic scorer for sentence-level AI detection."""
    lower = sentence.lower()
    words = re.findall(r"\b[a-zA-Z']+\b", sentence)
    word_count = len(words)

    matched_cliches = [c for c in AI_CLICHES if c in lower]
    reasons: List[str] = []
    score = 32

    # 1. Direct AI cliché phrases
    if matched_cliches:
        score += min(52, len(matched_cliches) * 24)
        reasons.append(
            f"Contains signature AI phraseology ({', '.join(repr(c) for c in matched_cliches[:3])})"
        )

    # 2. Structural AI patterns & intensifiers
    for pattern, reason_desc in AI_STRUCTURAL_PATTERNS:
        if re.search(pattern, lower):
            score += 14
            if reason_desc not in reasons:
                reasons.append(reason_desc)

    # 3. Formal conjunctive adverb starters
    if re.match(
        r"^(Furthermore|Moreover|Additionally|Consequently|Ultimately|In conclusion|Overall|Notably|Importantly|Therefore|Thus)\b",
        sentence,
    ):
        score += 22
        reasons.append("Starts with formal conjunctive transition typical of LLM output")

    # 4. High abstract nominalization density (-tion, -ment, -ity, -ance, -ence, -ive)
    if word_count >= 8:
        nominalizations = [
            w
            for w in words
            if len(w) >= 7
            and w.lower().endswith(("tion", "tions", "ment", "ments", "ity", "ities", "ance", "ence", "iveness"))
        ]
        nom_ratio = len(nominalizations) / word_count
        if nom_ratio >= 0.14:
            score += 18
            reasons.append(
                f"High density of abstract Latinate nouns ({', '.join(nominalizations[:3])})"
            )
        elif nom_ratio >= 0.08:
            score += 10

    # 5. Average word length & lack of contractions in medium/long sentences
    avg_word_len = (sum(len(w) for w in words) / word_count) if word_count else 0
    has_contraction = bool(re.search(r"\b\w+'(t|re|ve|ll|m|d|s)\b", lower))
    if word_count >= 14 and avg_word_len >= 5.2 and not has_contraction:
        score += 15
        reasons.append("Elevated lexical formality with zero natural contractions")

    # 6. Balanced uniform clause length + document uniformity
    if 15 <= word_count <= 32 and "," in sentence and not re.search(r"[!?;—()]", sentence):
        score += 12
        if doc_uniformity >= 65:
            score += 8
            reasons.append("Uniform sentence length and symmetrical clause cadence")

    # 7. Human authenticity signals reduce AI score
    if re.search(
        r"\b(honestly|weird|nasty|annoying|let's|we're|didn't|don't|can't|won't|folks|quick|heads-up|btw|imo|yeah|pretty|super|stuff|guys)\b",
        lower,
    ):
        score -= 28
    if re.search(r"\b(\d+%|\d+am|\d+pm|v\d+\.\d+|q[1-4]|monday|tuesday|wednesday|thursday|friday)\b", lower):
        score -= 20

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
    Uses Gemini Pro (or configured External LLM API) with forensic linguistic fallback.
    """
    sentences = split_sentences(text)
    metrics = compute_linguistic_metrics(sentences)
    doc_uniformity = metrics.get("uniformity_score", 50)

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
                "Analyze the given JSON list of sentences for AI-generated patterns (ChatGPT, Gemini, Claude) "
                "such as low burstiness, overused transitions ('Furthermore', 'Moreover', 'delve', 'tapestry', "
                "'testament', 'strategic imperative'), robotic symmetry, and vague corporate abstractions.\n\n"
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
                '        {"label": "Natural & Direct", "tone": "natural", "text": "<authentic human rewrite>"},\n'
                '        {"label": "Executive Crisp", "tone": "executive", "text": "<sharp, specific business rewrite>"},\n'
                '        {"label": "Conversational", "tone": "casual", "text": "<warm, grounded human rewrite>"}\n'
                "      ]\n"
                "    }\n"
                "  ]\n"
                "}"
            )
            user_prompt = (
                "Analyze these sentences and provide 3 human rewrite suggestions for any sentence with status 'ai' or 'mixed':\n"
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
                            or ["Evaluated by Gemini Pro forensic model"],
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
            return {
                "overall_ai_probability": overall_ai,
                "overall_human_probability": 100 - overall_ai,
                "verdict": llm_result.get("verdict")
                or _verdict_from_score(overall_ai),
                "summary": llm_result.get("summary")
                or f"Analyzed via {llm_client.provider.upper()} ({llm_client.model}).",
                "provider_used": llm_client.provider,
                "model_used": llm_client.model,
                "is_live_llm": True,
                "llm_error": None,
                "metrics": metrics,
                "sentences": enriched_sentences,
            }
        except Exception as exc:
            llm_error_msg = str(exc)
    else:
        llm_error_msg = None

    # Multi-signal forensic linguistic analysis
    analyzed_sentences = [
        _heuristic_sentence_analysis(i, s, doc_uniformity)
        for i, s in enumerate(sentences)
    ]
    overall_ai = int(
        round(
            sum(s["ai_probability"] for s in analyzed_sentences)
            / len(analyzed_sentences)
        )
    )
    summary_text = (
        f"Evaluated {len(sentences)} sentences across burstiness ({metrics['burstiness_score']}/100), "
        f"clause uniformity ({metrics['uniformity_score']}%), and {metrics['cliche_count']} AI signature patterns."
    )
    return {
        "overall_ai_probability": overall_ai,
        "overall_human_probability": 100 - overall_ai,
        "verdict": _verdict_from_score(overall_ai),
        "summary": summary_text,
        "provider_used": llm_client.provider,
        "model_used": llm_client.model,
        "is_live_llm": False,
        "llm_error": llm_error_msg,
        "metrics": metrics,
        "sentences": analyzed_sentences,
    }


def _verdict_from_score(score: int) -> str:
    if score >= 65:
        return "Likely AI-Generated"
    if score >= 40:
        return "Mixed AI & Human"
    return "Authentic Human Writing"
