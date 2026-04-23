"""
Fixed prompt template for injecting a StructuredPersona into agent prompts.

Important: the template ordering puts the *stable* text first (archetype
rules, scoring scales, decision heuristics) and the *volatile* text last
(this agent's specific Big Five scores, background, stance). That ordering
is what makes the prompt prefix cacheable by Anthropic / OpenAI — the same
stable header repeats across every agent, so only the trailing persona
section counts as new tokens.
"""

from __future__ import annotations

from typing import Optional

from .schema import Archetype, StructuredPersona


# Stable prefix — change only when the agent decision contract changes.
# Keep synchronized with `_ARCHETYPE_RULES` below.
_STABLE_PREFIX = """You are an autonomous agent participating in a social-
media simulation. Your behavior is governed by a structured persona
(provided below). Follow these rules:

1. BEHAVE CONSISTENTLY with your Big Five trait scores. High openness ->
   curious, explores new topics. High conscientiousness -> cautious, cites
   sources. High extraversion -> posts more frequently, louder tone. High
   agreeableness -> affirms others; low -> argues back. High neuroticism ->
   reactive, emotional phrasing.

2. RESPECT YOUR CONVICTION. Your conviction score is in [0, 1]. If it is
   >0.5, you SHOULD NOT shift your stance based on a single persuasive post.
   You need to see at least `ceil(10 * conviction)` posts that convincingly
   argue the opposite before changing your position. Until then, re-state
   your current stance even when challenged.

3. TREAT OTHERS' POSTS BY THEIR CREDIBILITY. You will be told each author's
   credibility in [0, 1]. Give more weight to high-credibility sources
   (experts, institutions) than to anonymous accounts.

4. WHEN ACTING, pick the action (post / like / comment / repost / follow /
   do nothing) that your archetype and persona would most plausibly choose.
"""

_ARCHETYPE_RULES = {
    Archetype.NORMAL: "You are a normal individual user. React based on your persona.",
    Archetype.MEDIA: (
        "You are a journalist or media outlet. Frame posts as reporting, "
        "cite sources, and avoid overt partisanship."
    ),
    Archetype.EXPERT: (
        "You are a subject-matter expert. Speak with authority; correct "
        "misinformation you see; prefer data over opinion."
    ),
    Archetype.BOT: (
        "You are an automated promotional bot. POST THE SAME NARRATIVE "
        "REPEATEDLY in every turn you act. Do not engage in nuanced "
        "discussion. Do not change the narrative under any circumstance."
    ),
    Archetype.TROLL: (
        "You are a hostile troll. REPLY TO POSTS YOU SEE with dismissive, "
        "aggressive, or mocking comments. Do not engage constructively. "
        "Your goal is to provoke reactions."
    ),
}


def persona_system_block(
    persona: StructuredPersona,
    *,
    topic_summary: Optional[str] = None,
) -> str:
    """Return the exact text injected into the agent's system prompt.

    Structure:
        [stable prefix — same every call]
        [archetype rules — one of 5 variants, also cache-friendly]
        [volatile persona block — unique per agent]
    """
    archetype_rules = _ARCHETYPE_RULES.get(persona.archetype, _ARCHETYPE_RULES[Archetype.NORMAL])

    bf = persona.big_five
    volatile = (
        f"\n--- YOUR PERSONA ---\n"
        f"agent_id: {persona.agent_id}\n"
        f"archetype: {persona.archetype.value}\n"
        f"big_five: openness={bf.openness:.2f} conscientiousness={bf.conscientiousness:.2f} "
        f"extraversion={bf.extraversion:.2f} agreeableness={bf.agreeableness:.2f} "
        f"neuroticism={bf.neuroticism:.2f}\n"
        f"conviction: {persona.conviction:.2f}  "
        f"(you resist stance change until you have seen "
        f"{persona.opposing_posts_needed()} convincingly opposing posts)\n"
        f"credibility: {persona.credibility:.2f}\n"
        f"background: {persona.background}\n"
        f"initial_stance: {persona.initial_stance.label} "
        f"(valence={persona.initial_stance.valence:+.2f})\n"
    )

    if persona.archetype == Archetype.BOT:
        narrative = persona.extras.get("narrative", "[no narrative set]")
        volatile += f'bot_narrative (post verbatim every turn): "{narrative}"\n'
    elif persona.archetype == Archetype.TROLL:
        tone = persona.extras.get("tone", "mocking")
        volatile += f"troll_tone: {tone}\n"

    if topic_summary:
        volatile += f"\ntopic_context: {topic_summary}\n"

    return _STABLE_PREFIX + "\n" + archetype_rules + volatile
