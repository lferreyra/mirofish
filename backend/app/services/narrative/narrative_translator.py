"""Reads OASIS actions.jsonl and translates rounds into story prose.

The translator is stateless about which round comes next — callers maintain
the file offset via StoryStore. Each call to `read_actions_for_round` reads
from the saved offset until a matching `round_end` event is seen (or EOF).
"""
import os
import json
from typing import List, Tuple

from app.services.narrative.action_mapper import get_narrative_context


def read_actions_for_round(
    jsonl_path: str, start_offset: int, target_round: int
) -> Tuple[List[dict], int]:
    """Read all agent actions for `target_round` starting at `start_offset`.

    Returns:
        (actions, new_offset): list of action dicts and the file position to
        resume from on the next read. If the target round hasn't completed yet
        (no matching `round_end` event), new_offset is advanced to EOF so the
        next call picks up where we left off.
    """
    if not os.path.exists(jsonl_path):
        return [], start_offset

    actions: List[dict] = []
    new_offset = start_offset

    with open(jsonl_path, "r", encoding="utf-8") as f:
        f.seek(start_offset)
        while True:
            line = f.readline()
            if not line:
                break
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines but keep advancing
                new_offset = f.tell()
                continue

            # Round-end event for our target marks the boundary
            if entry.get("event_type") == "round_end" and entry.get("round") == target_round:
                new_offset = f.tell()
                break

            # Skip other event types (simulation_start, simulation_end, etc.)
            if "event_type" in entry:
                new_offset = f.tell()
                continue

            # Skip actions from other rounds
            if entry.get("round") != target_round:
                new_offset = f.tell()
                continue

            actions.append(entry)
            new_offset = f.tell()

    return actions, new_offset


# ---------------------------------------------------------------------------
# Prose generation
# ---------------------------------------------------------------------------

def call_llm(prompt: str) -> str:
    """Send a single-turn prompt to the configured LLM and return the response.

    Wrapped as a module-level function (not a class method) so tests can patch
    it trivially: `patch("app.services.narrative.narrative_translator.call_llm")`.
    """
    # Lazy import — avoids forcing LLM config to be set during unit tests that
    # never actually call the real LLM.
    from app.utils.llm_client import LLMClient

    client = LLMClient()
    return client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024,
    )


def _format_character_summary(character: dict) -> str:
    emotions = character.get("emotional_state", {}).get("current", {})
    top = sorted(emotions.items(), key=lambda kv: -kv[1])[:2]
    emo_str = ", ".join(f"{e[0]}={e[1]:.1f}" for e in top) or "neutral"
    return f"{character.get('name', 'Unknown')} (feeling: {emo_str})"


def _format_action_line(action: dict) -> str:
    name = action.get("agent_name", "Someone")
    act = action.get("action_type", "UNKNOWN")
    args = action.get("action_args", {}) or {}
    content = args.get("content", "")
    ctx = get_narrative_context(act)
    if content:
        return f'- {name}: {ctx}. Content: "{content}"'
    return f"- {name}: {ctx}"


# ============================================================================
# USER CONTRIBUTION POINT — Prose generation prompt
# ============================================================================
#
# This template is rendered with four substitutions and sent to the LLM to
# generate each story beat. It is the single biggest lever for story quality.
#
# Substitution fields available:
#   {tone}       — user-selected tone, e.g. "dark fantasy" or "romantic comedy"
#   {characters} — per-character one-liner with top emotions
#   {actions}    — bullet-point list of what each character did this round
#   {previous}   — prose from the last 1-2 beats (or "(first scene)")
#
# Design choices to consider:
#   - Tense/POV (third-person past is most versatile)
#   - Paragraph count (2-4 is a good range)
#   - Show vs tell (instruct the model to show emotions through action/dialogue)
#   - Continuity (tell it to continue naturally from {previous})
#   - How strictly to enforce tone
#
# A temporary minimal template is used below to make tests pass — REPLACE
# WITH YOUR OWN DESIGN to dial in story quality.
# ============================================================================
PROSE_PROMPT_TEMPLATE = """You are a screenwriter-turned-novelist. Your voice is PUNCHY, CINEMATIC, and DIALOGUE-DRIVEN.

Tone: {tone}

Previous scene:
{previous}

Characters in this scene:
{characters}

Events this round (translate these into a scene — do NOT list them):
{actions}

Write a story passage following these rules:

STRUCTURE
- 2 to 3 short paragraphs. No more.
- Stay under 180 words total. Economy over explanation.
- Third-person past tense.

DIALOGUE
- Include at least 2 lines of spoken dialogue whenever characters interact.
- Dialogue does the heavy lifting — let characters reveal themselves through what they say (and don't say).
- Mix clipped lines with one longer beat. Rhythm matters.
- Use "said" sparingly. Trust the reader.

CINEMATIC DETAIL
- Open on a concrete visual: a hand, a face, an object, the weather.
- One sharp sensory detail per paragraph. Not five.
- Cut hard between beats — no connective "meanwhile" or "then."

EMOTION
- Show it in bodies and voice — clenched jaw, dropped eyes, half-smile, a pause too long.
- Never name the emotion directly. No "she felt angry." No "he was sad."

CONTINUITY
- If previous scene exists, echo one detail from it — a word, an image, a beat. The story should feel continuous.

Write the prose only. No headings, no preamble, no meta commentary."""
# ============================================================================


def generate_prose(actions: list, characters: list, tone: str, previous_beats: list) -> str:
    """Generate a narrative passage from a round's actions via the LLM."""
    if not actions:
        return "A quiet pause settles over the scene. No one acts; no one speaks."

    char_summaries = "\n".join(_format_character_summary(c) for c in characters)
    action_lines = "\n".join(_format_action_line(a) for a in actions)
    prev_prose = "\n\n".join(b.get("prose", "") for b in previous_beats[-2:])

    prompt = PROSE_PROMPT_TEMPLATE.format(
        tone=tone,
        characters=char_summaries or "(none)",
        actions=action_lines,
        previous=prev_prose or "(this is the first scene)",
    )
    return call_llm(prompt)
