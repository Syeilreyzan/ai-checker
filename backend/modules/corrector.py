import re
from typing import Any, Dict, List, Optional
from .llm_client import LLMClient

# Comprehensive AI-to-Human vocabulary & phrase de-AI dictionary
# Targets the high-probability LLM tokens flagged by GPTZero, ZeroGPT, QuillBot, and Originality.ai
PHRASE_TRANSFORMS = [
    # Opening transitions & framing
    (r"^In today's rapidly evolving [^,]+,\s*", "Right now, "),
    (r"^In today's fast-paced [^,]+,\s*", "Today, "),
    (r"^In today's increasingly [^,]+,\s*", "Right now, "),
    (r"^In today's [^,]+ landscape,\s*", "Today, "),
    (r"^In the modern [^,]+,\s*", "Today, "),
    (r"^When it comes to ([^,]+),\s*", r"For \1, "),
    (r"^It is important to note that\s*", ""),
    (r"^It is worth noting that\s*", ""),
    (r"^It is crucial to understand that\s*", ""),
    (r"^It is essential to recognize that\s*", ""),
    (r"^It is crucial to\s*", "We need to "),
    (r"^It is essential to\s*", "You have to "),
    (r"^It is imperative to\s*", "We must "),
    (r"^There is no doubt that\s*", ""),
    (r"^Furthermore,\s*", "On top of that, "),
    (r"^Moreover,\s*", "Plus, "),
    (r"^Additionally,\s*", "Also, "),
    (r"^Consequently,\s*", "Because of that, "),
    (r"^Therefore,\s*", "So "),
    (r"^Thus,\s*", "So "),
    (r"^Hence,\s*", "That means "),
    (r"^Nevertheless,\s*", "Still, "),
    (r"^Nonetheless,\s*", "Even so, "),
    (r"^However,\s*", "But "),
    (r"^Ultimately,\s*", "In the end, "),
    (r"^In conclusion,\s*", "Bottom line: "),
    (r"^To summarize,\s*", "In short: "),
    (r"^Overall,\s*", "All in all, "),

    # Classic LLM multi-word clichés
    (r"\bis not merely an option, but a strategic imperative for\b", "is a must if we want"),
    (r"\bis not merely\b", "isn't just"),
    (r"\bis not only\b", "isn't just"),
    (r"\bbut also\b", "and it also"),
    (r"\bstands at the precipice of a transformative journey that will redefine\b", "is about to change"),
    (r"\bBy delving into the intricate tapestry of\b", "When we look closely at"),
    (r"\bby delving into\b", "by digging into"),
    (r"\bdelving into\b", "digging into"),
    (r"\bdelve into\b", "dig into"),
    (r"\bintricate tapestry of\b", "mix of"),
    (r"\bunlock unprecedented operational efficiencies across all verticals\b", "save real time and money across every team"),
    (r"\bunlock unprecedented\b", "open up new"),
    (r"\boperational efficiencies\b", "time savings"),
    (r"\boperational efficiency\b", "speed and efficiency"),
    (r"\boperational overhead\b", "day-to-day costs"),
    (r"\bacross all verticals\b", "across every team"),
    (r"\bacross various sectors\b", "in different industries"),
    (r"\bfoster a culture of continuous innovation\b", "keep teams experimenting"),
    (r"\bfoster a culture of\b", "build real"),
    (r"\bmaintaining unwavering commitment to excellence\b", "keeping quality high"),
    (r"\bunwavering commitment to\b", "steady focus on"),
    (r"\bunwavering dedication\b", "hard work"),
    (r"\bthis holistic approach serves as a testament to our vision of paving the way toward a brighter, more interconnected future\b", "this approach shows how we're building practical tools that actually work together"),
    (r"\bserves as a testament to\b", "proves"),
    (r"\btestament to\b", "proof of"),
    (r"\bpaving the way toward\b", "setting up"),
    (r"\bpaving the way for\b", "making room for"),
    (r"\brepresents a paradigm shift in\b", "completely changes"),
    (r"\bparadigm shift\b", "major change"),
    (r"\bseamlessly orchestrate future deployments with minimal friction\b", "roll out future updates without the headaches"),
    (r"\bwith minimal friction\b", "smoothly"),
    (r"\bcomprehensive observability metrics\b", "clearer monitoring data"),
    (r"\bactionable insights\b", "practical takeaways"),
    (r"\bdata-driven insights\b", "real data"),
    (r"\bvast datasets\b", "large amounts of data"),
    (r"\brepetitive tasks\b", "routine busywork"),
    (r"\bdaily workflows\b", "day-to-day work"),
    (r"\btechnological advancements\b", "new tools"),
    (r"\bcompetitive market\b", "tough market"),
    (r"\bplays a crucial role in\b", "makes a huge difference in"),
    (r"\bplays a vital role in\b", "matters a lot for"),
    (r"\bplays a pivotal role in\b", "is central to"),
    (r"\bplays an essential role in\b", "is key to"),
    (r"\bplays a key role in\b", "drives"),
    (r"\bunderscores the importance of\b", "shows why we need"),
    (r"\bhighlights the importance of\b", "shows why we need"),

    # High-frequency LLM verbs & adjectives -> everyday human words
    (r"\bleveraging cutting-edge\b", "using modern"),
    (r"\bcutting-edge\b", "modern"),
    (r"\bstate-of-the-art\b", "modern"),
    (r"\bleveraging\b", "using"),
    (r"\bleverage\b", "use"),
    (r"\butilizing\b", "using"),
    (r"\butilize\b", "use"),
    (r"\butilization\b", "use"),
    (r"\bfacilitates\b", "helps"),
    (r"\bfacilitate\b", "help"),
    (r"\bfacilitating\b", "helping"),
    (r"\bsignificantly enhance\b", "boost"),
    (r"\bsignificantly enhances\b", "boosts"),
    (r"\bsignificantly improve\b", "sharply improve"),
    (r"\benhances\b", "improves"),
    (r"\benhance\b", "improve"),
    (r"\benhancing\b", "improving"),
    (r"\boptimizing\b", "tuning"),
    (r"\boptimize\b", "fine-tune"),
    (r"\bempowering\b", "helping"),
    (r"\bempowers\b", "lets"),
    (r"\bempower\b", "help"),
    (r"\bstreamlining\b", "simplifying"),
    (r"\bstreamline\b", "simplify"),
    (r"\bprioritizes\b", "puts first"),
    (r"\bprioritize\b", "focus on"),
    (r"\bprioritizing\b", "focusing on"),
    (r"\bdemonstrates\b", "shows"),
    (r"\bdemonstrate\b", "show"),
    (r"\buncovering\b", "finding"),
    (r"\buncover\b", "find"),
    (r"\bintegrating\b", "building"),
    (r"\bimplementing\b", "rolling out"),
    (r"\bimplementation\b", "rollout"),
    (r"\borganizations\b", "companies"),
    (r"\borganization\b", "company"),
    (r"\bindividuals\b", "people"),
    (r"\bstakeholders\b", "teams and partners"),
    (r"\bmethodology\b", "method"),
    (r"\bmethodologies\b", "methods"),
    (r"\bcapabilities\b", "tools"),
    (r"\bfunctionalities\b", "features"),
    (r"\bobjectives\b", "goals"),
    (r"\binitiatives\b", "projects"),
    (r"\bseamlessly\b", "smoothly"),
    (r"\bholistic\b", "complete"),
    (r"\brobust\b", "solid"),
    (r"\bcomprehensive\b", "full"),
    (r"\bpivotal\b", "key"),
    (r"\bparamount\b", "top"),
    (r"\bcrucial\b", "key"),
    (r"\bimperative\b", "essential"),
    (r"\bunprecedented\b", "major"),
    (r"\btransformative\b", "game-changing"),
    (r"\bincreasingly\b", "more and more"),
    (r"\beffectively\b", "well"),
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bfor the purpose of\b", "to"),
    (r"\ba wide range of\b", "many"),
    (r"\ba variety of\b", "different"),
]

CONTRACTIONS = [
    (r"\bIt is\b", "It's"),
    (r"\bit is\b", "it's"),
    (r"\bThat is\b", "That's"),
    (r"\bthat is\b", "that's"),
    (r"\bThere is\b", "There's"),
    (r"\bthere is\b", "there's"),
    (r"\bWe are\b", "We're"),
    (r"\bwe are\b", "we're"),
    (r"\bThey are\b", "They're"),
    (r"\bthey are\b", "they're"),
    (r"\bYou are\b", "You're"),
    (r"\byou are\b", "you're"),
    (r"\bdo not\b", "don't"),
    (r"\bDo not\b", "Don't"),
    (r"\bdoes not\b", "doesn't"),
    (r"\bdid not\b", "didn't"),
    (r"\bcannot\b", "can't"),
    (r"\bcan not\b", "can't"),
    (r"\bwill not\b", "won't"),
    (r"\bis not\b", "isn't"),
    (r"\bare not\b", "aren't"),
    (r"\bhave not\b", "haven't"),
    (r"\bhas not\b", "hasn't"),
    (r"\bI am\b", "I'm"),
    (r"\bwe have\b", "we've"),
    (r"\bWe have\b", "We've"),
    (r"\bwe will\b", "we'll"),
    (r"\bWe will\b", "We'll"),
]


def _cap(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


def _apply_contractions(text: str) -> str:
    out = text
    for pat, repl in CONTRACTIONS:
        out = re.sub(pat, repl, out)
    return out


def _restructure_ai_skeleton(sentence: str, idx_seed: int = 0) -> Dict[str, str]:
    """
    Deep syntactic restructuring to break AI sentence skeletons and inject high burstiness
    (varying sentence length with short punchy sentences + em-dashes + contractions)
    so external detectors (ZeroGPT, GPTZero, QuillBot) score the text as Human.
    """
    s = sentence.strip()
    for pat, repl in PHRASE_TRANSFORMS:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)
    s = _apply_contractions(s)
    s = _cap(re.sub(r"\s+", " ", s))

    # Pattern 1: "By [doing X], [subject] can/will [do Y]" -> flip order or break into 2 punchy sentences
    m_by = re.match(
        r"^(?:By|Through|When)\s+([^,]{8,75}),\s+(.+)$", s, flags=re.IGNORECASE
    )
    if m_by:
        method_clause = m_by.group(1).strip()
        main_clause = _cap(m_by.group(2).strip().rstrip("."))
        natural = f"{main_clause} when you focus on {method_clause}."
        exec_ver = f"{main_clause}—especially by {method_clause}."
        casual = f"Here's the trick: {main_clause[0].lower() + main_clause[1:]} just by {method_clause}."
        return {"natural": natural, "executive": exec_ver, "casual": casual}

    # Pattern 2: "[Subject] is transforming/changing/redefining [X] by [Y]"
    m_by_mid = re.match(r"^([^,]{12,90}?)\s+by\s+([a-z]+ing\s+.+)$", s)
    if m_by_mid:
        first_part = _cap(m_by_mid.group(1).strip().rstrip("."))
        second_part = m_by_mid.group(2).strip().rstrip(".")
        natural = f"{first_part}. How? By {second_part}."
        exec_ver = f"{first_part}—specifically by {second_part}."
        casual = f"{first_part}, mostly because it's {second_part}."
        return {"natural": natural, "executive": exec_ver, "casual": casual}

    # Pattern 3: Sentence with ", while [gerund]..." or " while [gerund]..."
    m_while = re.match(r"^(.+?),\s*while\s+(.+)$", s, flags=re.IGNORECASE)
    if m_while:
        part1 = _cap(m_while.group(1).strip().rstrip("."))
        part2 = m_while.group(2).strip().rstrip(".")
        natural = f"{part1}—all while {part2}."
        exec_ver = f"{part1}. At the same time, it keeps {part2}."
        casual = f"{part1}, and you're still {part2}."
        return {"natural": natural, "executive": exec_ver, "casual": casual}

    # Pattern 4: Long sentence (>17 words) with a comma -> split into 2 sentences for high burstiness!
    words = s.split()
    if len(words) >= 17 and "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and len(parts[0].split()) >= 3 and len(parts[1].split()) >= 5:
            p1 = _cap(parts[0].rstrip("."))
            p2 = _cap(parts[1].rstrip("."))
            if len(parts[0].split()) <= 5:
                # Short transition phrase at start: turn it into a short punchy sentence or strip it
                natural = f"{p2}."
                exec_ver = f"{p2}—and that's what counts."
                casual = f"Look: {p2[0].lower() + p2[1:]}."
            else:
                natural = f"{p1}. On top of that, {p2[0].lower() + p2[1:]}."
                exec_ver = f"{p2}—{p1[0].lower() + p1[1:]}."
                casual = f"{p1}, which basically means {p2[0].lower() + p2[1:]}."
            return {"natural": natural, "executive": exec_ver, "casual": casual}

    # Pattern 5: Long sentence without comma (>16 words) -> break around "that", "which", "and", or "to"
    if len(words) >= 16:
        m_split = re.match(
            r"^(.{25,95}?)\s+(?:and|which|that)\s+(.{15,})$", s
        )
        if m_split:
            p1 = _cap(m_split.group(1).strip().rstrip("."))
            p2 = m_split.group(2).strip().rstrip(".")
            natural = f"{p1}—and it {p2}."
            exec_ver = f"{p1}. Plus, that {p2}."
            casual = f"{p1}, so it naturally {p2}."
            return {"natural": natural, "executive": exec_ver, "casual": casual}

    # Default high-burstiness human variations
    base_clean = re.sub(
        r"^(Right now,|Today,|On top of that,|Plus,|Also,|Because of that,|So |Still,|Even so,|But |In the end,|Bottom line:|In short:|All in all,)\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    base_clean = _cap(base_clean.rstrip("."))

    hooks = [
        ("Here's the reality:", "What matters most:"),
        ("Simply put,", "In short:"),
        ("Think about it this way:", "Bottom line:"),
    ]
    h_casual, h_exec = hooks[idx_seed % len(hooks)]

    natural = f"{s.rstrip('.')}—and that makes a real difference." if s == sentence.strip() else s
    exec_ver = f"{base_clean}." if base_clean != natural.rstrip(".") else f"{h_exec} {base_clean[0].lower() + base_clean[1:]}."
    casual = f"{h_casual} {base_clean[0].lower() + base_clean[1:]}."

    return {"natural": natural, "executive": exec_ver, "casual": casual}


def generate_fallback_suggestions(sentence: str, idx_seed: int = 0) -> List[Dict[str, str]]:
    """
    Generates 3 high-burstiness, high-perplexity human rewrites designed to defeat
    external AI detectors (ZeroGPT, GPTZero, QuillBot).
    """
    variants = _restructure_ai_skeleton(sentence, idx_seed=idx_seed)
    return [
        {
            "label": "Natural & Direct (Anti-AI Detector)",
            "tone": "natural",
            "text": variants["natural"],
        },
        {
            "label": "Executive Crisp",
            "tone": "executive",
            "text": variants["executive"],
        },
        {
            "label": "Conversational & High-Burstiness",
            "tone": "casual",
            "text": variants["casual"],
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
    Uses Gemini Pro (or configured External LLM API) with explicit anti-detector burstiness/perplexity rules.
    """
    if llm_client.is_configured:
        try:
            system_prompt = (
                "You are an expert human ghostwriter whose rewrites ALWAYS score 0% AI / 100% Human "
                "on GPTZero, ZeroGPT, Originality.ai, and QuillBot.\n"
                "To defeat statistical AI detectors, you MUST follow these strict rules:\n"
                "1. HIGH BURSTINESS: Break long 20-word sentences into a mix of a very short punchy sentence (3-6 words) "
                "and a conversational clause, or use em-dashes (—) and contractions (it's, don't, we're, can't, won't).\n"
                "2. HIGH PERPLEXITY: Never use standard LLM verbs/nouns (transforming, leveraging, utilizing, enhancing, "
                "fostering, seamless, comprehensive, crucial, pivotal, landscape, paradigm, delve, tapestry, testament, "
                "operational, actionable insights, workflows, organizations, individuals). Use plain, everyday human words "
                "(use, fix, cut, build, teams, people, busywork, day-to-day).\n"
                "3. DESTROY AI SYNTAX: Never start with 'By [verb]-ing...' or 'Furthermore/Moreover/Additionally/Ultimately'.\n\n"
                "Return ONLY valid JSON with this exact schema:\n"
                "{\n"
                '  "suggestions": [\n'
                '    {"label": "Natural & Direct (Anti-AI Detector)", "tone": "natural", "text": "<rewrite 1>"},\n'
                '    {"label": "Executive Crisp", "tone": "executive", "text": "<rewrite 2>"},\n'
                '    {"label": "Conversational & High-Burstiness", "tone": "casual", "text": "<rewrite 3>"}\n'
                "  ],\n"
                '  "what_changed": "<1 short sentence explaining how perplexity and burstiness were increased>"\n'
                "}"
            )
            user_prompt = (
                f"Target AI sentence to humanize so external AI detectors score it 100% Human:\n\"{sentence}\"\n\n"
                f"Preferred primary tone: {tone}\n"
                f"Custom user instruction: {custom_instruction or 'Rewrite with high burstiness, contractions, and plain human words.'}\n"
                f"Surrounding document context:\n{context_text[:1200]}"
            )
            result = await llm_client.complete_json(system_prompt, user_prompt)
            suggestions = result.get("suggestions") or generate_fallback_suggestions(sentence)
            return {
                "original_sentence": sentence,
                "suggestions": suggestions,
                "what_changed": result.get(
                    "what_changed",
                    "Restructured AI clause symmetry, added human contractions, and injected burstiness.",
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
        "what_changed": "Broke uniform LLM clause cadence, replaced AI vocabulary, and added human burstiness.",
        "provider_used": llm_client.provider,
        "is_live_llm": False,
    }
