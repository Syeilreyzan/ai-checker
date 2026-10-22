from typing import List, Dict

SAMPLES: List[Dict[str, str]] = [
    {
        "id": "ai-corporate",
        "title": "100% AI — Corporate Strategy Memo",
        "badge": "High AI",
        "description": "Classic ChatGPT-style corporate announcement filled with AI tropes and uniform cadence.",
        "text": (
            "In today's rapidly evolving digital landscape, leveraging cutting-edge artificial intelligence "
            "is not merely an option, but a strategic imperative for sustainable growth. Furthermore, our organization "
            "stands at the precipice of a transformative journey that will redefine how we deliver value to our stakeholders. "
            "By delving into the intricate tapestry of data-driven insights, we can unlock unprecedented operational efficiencies "
            "across all verticals. Moreover, it is crucial to foster a culture of continuous innovation while maintaining "
            "unwavering commitment to excellence. Ultimately, this holistic approach serves as a testament to our vision "
            "of paving the way toward a brighter, more interconnected future."
        ),
    },
    {
        "id": "mixed-report",
        "title": "Mixed — Product Launch Post-Mortem",
        "badge": "Mixed (AI + Human)",
        "description": "A human manager's rough notes mixed with paragraphs polished by an LLM.",
        "text": (
            "We shipped v2.4 on Tuesday at 2am after fixing that nasty Redis timeout bug in checkout. "
            "Honestly, the staging environment didn't catch it because our mock traffic was way too low. "
            "Furthermore, the implementation of our novel caching architecture represents a paradigm shift in system reliability "
            "and serves as a testament to the team's unwavering dedication. "
            "Moreover, by delving into comprehensive observability metrics, we can seamlessly orchestrate future deployments "
            "with minimal friction. "
            "Next sprint, Sarah and I are going to rewrite the load test script so we don't get paged on a Tuesday night again."
        ),
    },
    {
        "id": "human-note",
        "title": "100% Human — Founder Slack Update",
        "badge": "Human Written",
        "description": "Natural human writing with high burstiness, varied sentence length, and specific details.",
        "text": (
            "Quick heads-up on the Q3 numbers before tomorrow's board call. "
            "Enterprise renewals came in 14% higher than we projected in July—mostly because Acme Corp expanded their seats early. "
            "Self-serve churn is still annoying me though. It ticked up from 3.1% to 3.6%, and almost half of the exit surveys "
            "mentioned the confusing onboarding wizard. Let's scrap the 5-step flow this week and just drop new users straight into the dashboard."
        ),
    },
]
