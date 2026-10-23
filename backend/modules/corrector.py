import re
from typing import Any, Dict, List, Optional
from .llm_client import LLMClient

REPLACEMENT_RULES = [
    (r"\bIn today's rapidly evolving digital landscape,\s*", "Right now, "),
    (r"\bIn today's fast-paced world,\s*", "Today, "),
    (r"\bIn today's competitive landscape,\s*", "In practice, "),
    (r"\bFurthermore,\s*", "On top of that, "),
    (r"\bMoreover,\s*", "Also, "),
    (r"\bAdditionally,\s*", "Plus, "),
    (r"\bConsequently,\s*", "So, "),
    (r"\bUltimately,\s*", "In the end, "),
    (r"\bIn conclusion,\s*", "Bottom line: "),
    (r"\bIt is important to note that\s*", ""),
    (r"\bIt is worth noting that\s*", ""),
    (r"\bIt is crucial to\s*", "We need to "),
    (r"\bIt is essential to\s*", "We should "),
    (r"\bleveraging cutting-edge\b", "using modern"),
    (r"\bleveraging\b", "using"),
    (r"\bleverage\b", "use"),
    (r"\butilizing\b", "using"),
    (r"\butilize\b", "use"),
    (r"\bis not merely an option, but a strategic imperative for\b", "is essential for"),
    (r"\bis not just\b", "isn't just"),
    (r"\bis not merely\b", "isn't just"),
    (r"\bstands at the precipice of a transformative journey that will redefine\b", "is ready to reshape"),
    (r"\bBy delving into the intricate tapestry of\b", "By looking closely at"),
    (r"\bby delving into\b", "by examining"),
    (r"\bdelving into\b", "digging into"),
    (r"\bdelve into\b", "look into"),
    (r"\bunlock unprecedented operational efficiencies across all verticals\b", "save time and cut costs across teams"),
    (r"\bit is crucial to foster a culture of continuous innovation while maintaining unwavering commitment to excellence\b", "we need to keep experimenting without letting quality slip"),
    (r"\bthis holistic approach serves as a testament to our vision of paving the way toward a brighter, more interconnected future\b", "this plan shows how we're building practical tools that work together"),
    (r"\brepresents a paradigm shift in\b", "significantly improves"),
    (r"\bserves as a testament to the team's unwavering dedication\b", "shows how hard the team worked"),
    (r"\bserves as a testament to\b", "proves"),
    (r"\bseamlessly orchestrate future deployments with minimal friction\b", "roll out future updates smoothly"),
    (r"\bcomprehensive observability metrics\b", "better monitoring data"),
    (r"\bplays a crucial role in\b", "drives"),
    (r"\bplays a vital role in\b", "shapes"),
    (r"\bplays a pivotal role in\b", "matters for"),
    (r"\bfoster a culture of\b", "build real"),
    (r"\bunwavering commitment to\b", "focus on"),
    (r"\bholistic approach to\b", "practical way to handle"),
    (r"\bholistic approach\b", "full plan"),
    (r"\bseamlessly integrate\b", "connect"),
    (r"\bseamlessly\b", "smoothly"),
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\b facilitates\b", " helps"),
    (r"\bfacilitate\b", "help"),
    (r"\benhances\b", "improves"),
    (r"\benhance\b", "improve"),
    (r"\boptimizing\b", "improving"),
    (r"\boptimize\b", "improve"),
    (r"\bempowering\b", "helping"),
    (r"\bempower\b", "help"),
    (r"\brobust\b", "solid"),
    (r"\bcomprehensive\b", "thorough"),
    (r"\bpivotal\b", "key"),
    (r"\bparamount\b", "critical"),
    (r"\bunderscores\b", "highlights"),
    (r"\bmeticulous\b", "careful"),
]


def _cap(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


def generate_fallback_suggestions(sentence: str) -> List[Dict[str, str]]:
    """Rule-based humanizer that strips AI clichés, breaks robotic cadence, and offers 3 distinct human rewrites."""
    natural = sentence.strip()
    for pattern, repl in REPLACEMENT_RULES:
        natural = re.sub(pattern, repl, natural, flags=re.IGNORECASE)

    # Apply human contractions
    contractions = [
        (r"\bit is\b", "it's"),
        (r"\bthat is\b", "that's"),
        (r"\bwe are\b", "we're"),
        (r"\bthey are\b", "they're"),
        (r"\bdo not\b", "don't"),
        (r"\bdoes not\b", "doesn't"),
        (r"\bcannot\b", "can't"),
        (r"\bwill not\b", "won't"),
    ]
    casual = natural
    for pat, repl in contractions:
        casual = re.sub(pat, repl, casual, flags=re.IGNORECASE)

    natural = _cap(re.sub(r"\s+", " ", natural))
    casual = _cap(re.sub(r"\s+", " ", casual))

    # Build a crisp executive variant by stripping introductory filler clauses
    exec_text = re.sub(
        r"^(Right now,|Today,|In practice,|On top of that,|Also,|Plus,|So,|In the end,|Bottom line:|Overall,|Generally,|Specifically,|Importantly,|Notably,)\s*",
        "",
        natural,
        flags=re.IGNORECASE,
    )
    # If sentence starts with "By [gerund]..., we can/are...", flip or tighten it
    exec_text = re.sub(
        r"^By\s+([^,]+),\s+we\s+can\s+",
        r"We can \2 by \1—" if False else r"We can ",
        exec_text,
        flags=re.IGNORECASE,
    )
    exec_text = _cap(re.sub(r"\s+", " ", exec_text))

    # If the input sentence didn't match specific rules, transform clause structure so all 3 options are genuinely different
    if natural == sentence.strip():
        stripped = re.sub(
            r"^(Furthermore|Moreover|Additionally|Consequently|Ultimately|However|Therefore|Thus|Hence|Notably|Importantly),?\s*",
            "",
            sentence.strip(),
            flags=re.IGNORECASE,
        )
        stripped = _cap(stripped)
        if "," in stripped and len(stripped.split()) > 16:
            parts = [p.strip() for p in stripped.split(",", 1)]
            if len(parts) == 2 and len(parts[0].split()) >= 4 and len(parts[1].split()) >= 5:
                first_clause = parts[0].rstrip(".")
                second_clause = _cap(parts[1])
                natural = f"{second_clause.rstrip('.')}—{first_clause[0].lower() + first_clause[1:]}."
                exec_text = f"{second_clause}"
                casual = f"Here's the thing: {stripped[0].lower() + stripped[1:]}"
            else:
                natural = f"In practice, {stripped[0].lower() + stripped[1:]}"
                exec_text = stripped
                casual = f"Simply put, {stripped[0].lower() + stripped[1:]}"
        else:
            natural = f"In practice, {stripped[0].lower() + stripped[1:]}"
            exec_text = stripped
            casual = f"Bottom line: {stripped[0].lower() + stripped[1:]}"

    return [
        {
            "label": "Natural & Direct",
            "tone": "natural",
            "text": natural,
        },
        {
            "label": "Executive Crisp",
            "tone": "executive",
            "text": exec_text if exec_text != natural else f"Key point: {exec_text[0].lower() + exec_text[1:]}",
        },
        {
            "label": "Conversational",
            "tone": "casual",
            "text": casual if casual not in (natural, exec_text) else f"Honestly, {exec_text[0].lower() + exec_text[1:]}",
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
        except Exception:
            pass

    fallback = generate_fallback_suggestions(sentence)
    return {
        "original_sentence": sentence,
        "suggestions": fallback,
        "what_changed": "Stripped formal LLM transitions and simplified multi-clause corporate jargon.",
        "provider_used": llm_client.provider,
        "is_live_llm": False,
    }
