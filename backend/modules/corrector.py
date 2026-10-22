import re
from typing import Any, Dict, List, Optional
from .llm_client import LLMClient

REPLACEMENT_RULES = [
    (r"\bIn today's rapidly evolving digital landscape,\s*", "Right now, "),
    (r"\bFurthermore,\s*", "On top of that, "),
    (r"\bMoreover,\s*", "Also, "),
    (r"\bAdditionally,\s*", "Plus, "),
    (r"\bConsequently,\s*", "So, "),
    (r"\bUltimately,\s*", "In the end, "),
    (r"\bIn conclusion,\s*", "Bottom line: "),
    (r"\bleveraging cutting-edge\b", "using modern"),
    (r"\bleveraging\b", "using"),
    (r"\bleverage\b", "use"),
    (r"\bis not merely an option, but a strategic imperative for\b", "is essential for"),
    (r"\bstands at the precipice of a transformative journey that will redefine\b", "is ready to reshape"),
    (r"\bBy delving into the intricate tapestry of\b", "By looking closely at"),
    (r"\bby delving into\b", "by examining"),
    (r"\bdelving into\b", "digging into"),
    (r"\bunlock unprecedented operational efficiencies across all verticals\b", "save time and cut costs across teams"),
    (r"\bit is crucial to foster a culture of continuous innovation while maintaining unwavering commitment to excellence\b", "we need to keep experimenting without letting quality slip"),
    (r"\bthis holistic approach serves as a testament to our vision of paving the way toward a brighter, more interconnected future\b", "this plan shows how we're building practical tools that work together"),
    (r"\brepresents a paradigm shift in\b", "significantly improves"),
    (r"\bserves as a testament to the team's unwavering dedication\b", "shows how hard the team worked"),
    (r"\bseamlessly orchestrate future deployments with minimal friction\b", "roll out future updates smoothly"),
    (r"\bcomprehensive observability metrics\b", "better monitoring data"),
]


def generate_fallback_suggestions(sentence: str) -> List[Dict[str, str]]:
    """Rule-based humanizer that strips AI clichés and offers 3 distinct human rewrites."""
    natural = sentence
    for pattern, repl in REPLACEMENT_RULES:
        natural = re.sub(pattern, repl, natural, flags=re.IGNORECASE)

    # Ensure first letter is capitalized
    natural = natural.strip()
    if natural:
        natural = natural[0].upper() + natural[1:]

    # Build a crisp executive variant
    exec_text = re.sub(
        r"^(Right now,|On top of that,|Also,|Plus,|In the end,)\s*",
        "",
        natural,
        flags=re.IGNORECASE,
    ).strip()
    if exec_text:
        exec_text = exec_text[0].upper() + exec_text[1:]

    # Build a conversational variant
    casual_text = natural
    if natural == sentence:
        # Generic de-puffing if no exact phrase rule matched
        casual_text = re.sub(
            r"^(Furthermore|Moreover|Additionally|Ultimately),?\s*",
            "",
            sentence,
            flags=re.IGNORECASE,
        )
        casual_text = casual_text[0].upper() + casual_text[1:] if casual_text else sentence
        natural = f"Simply put: {casual_text[0].lower() + casual_text[1:]}" if len(casual_text) > 1 else casual_text
        exec_text = casual_text

    return [
        {
            "label": "Natural & Direct",
            "tone": "natural",
            "text": natural,
        },
        {
            "label": "Executive Crisp",
            "tone": "executive",
            "text": exec_text,
        },
        {
            "label": "Conversational",
            "tone": "casual",
            "text": casual_text if casual_text != natural else f"Here's the reality: {exec_text[0].lower() + exec_text[1:]}",
        },
    ]


async def rewrite_flagged_sentence(
    sentence: str,
    context_text: str,
    tone: str,
    custom_instruction: Optional[str],
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Interactive Sentence Corrector Module.
    Uses External LLM API to rewrite an AI-flagged sentence into authentic human prose.
    """
    if llm_client.is_configured:
        try:
            system_prompt = (
                "You are an elite human editor specializing in rewriting robotic, AI-generated sentences "
                "into authentic, natural human writing with high burstiness, concrete verbs, and zero LLM clichés "
                "(never use 'delve', 'tapestry', 'testament', 'furthermore', 'moreover', 'paradigm', 'unwavering').\n\n"
                "Return ONLY valid JSON with this exact schema:\n"
                "{\n"
                '  "suggestions": [\n'
                '    {"label": "Natural & Direct", "tone": "natural", "text": "<rewrite 1>"},\n'
                '    {"label": "Executive Crisp", "tone": "executive", "text": "<rewrite 2>"},\n'
                '    {"label": "Conversational", "tone": "casual", "text": "<rewrite 3>"}\n'
                "  ],\n"
                '  "what_changed": "<1 short sentence explaining how the AI traits were fixed>"\n'
                "}"
            )
            user_prompt = (
                f"Target sentence to humanize:\n\"{sentence}\"\n\n"
                f"Preferred primary tone: {tone}\n"
                f"Custom user instruction: {custom_instruction or 'Make it sound 100% written by a real person.'}\n"
                f"Surrounding document context:\n{context_text[:1200]}"
            )
            result = await llm_client.complete_json(system_prompt, user_prompt)
            suggestions = result.get("suggestions") or generate_fallback_suggestions(sentence)
            return {
                "original_sentence": sentence,
                "suggestions": suggestions,
                "what_changed": result.get(
                    "what_changed",
                    "Removed synthetic transitions and replaced abstract buzzwords with direct human phrasing.",
                ),
                "provider_used": llm_client.provider,
                "is_live_llm": True,
            }
        except Exception as exc:
            pass

    fallback = generate_fallback_suggestions(sentence)
    return {
        "original_sentence": sentence,
        "suggestions": fallback,
        "what_changed": "Stripped formal LLM transitions and simplified multi-clause corporate jargon.",
        "provider_used": llm_client.provider,
        "is_live_llm": False,
    }
