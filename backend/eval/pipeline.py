"""
Orchestrates a minimal MiroFish pipeline for one dataset case.

Simplified flow compared to the live runner:

    1. Load dataset (seed.md + question.md + truth.json)
    2. Generate N personas (via MockRouter or live ModelRouter)
    3. Build a population with the configured mix (phase-4 knobs)
    4. Run `rounds` rounds. Each round, each agent either posts or
       abstains based on their extraversion + a deterministic draw.
       The post's valence is drawn from the persona's initial_stance
       (with noise scaled by 1 - conviction).
    5. Feed each post through the MemoryManager so Phase-2 / Phase-4
       features (importance, reflection, contradiction, credibility
       weighting) are actually exercised.
    6. Extract a Verdict from the public timeline.

The simplification is deliberate: we are grading the HARNESS, not the
underlying language model. A live run replaces MockRouter with the real
router and replaces step 4 with OASIS-driven agent actions, but the
verdict extraction + scoring is unchanged.
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.memory.in_memory import InMemoryBackend
from app.memory.manager import MemoryManager
from app.personas import (
    Archetype,
    CredibilityWeighter,
    PersonaGenerator,
    StanceInertia,
    StructuredPersona,
)
from app.personas.population import (
    build_bot_persona,
    build_population,
    build_troll_persona,
)
from app.personas.schema import StanceVector
from .determinism import seeded_random
from .mocks import MockRouter
from .scoring import Truth, Verdict
from .verdict import verdict_from_public_timeline


# --------------------------------------------------------------------------
# Dataset loading
# --------------------------------------------------------------------------

@dataclass
class DatasetCase:
    """A single (seed, question, truth) triple."""
    name: str
    path: str
    seed: str         # raw seed.md contents
    question: str     # raw question.md contents
    truth: Truth

    @classmethod
    def load(cls, case_dir: str) -> "DatasetCase":
        name = os.path.basename(os.path.normpath(case_dir))
        with open(os.path.join(case_dir, "seed.md"), encoding="utf-8") as fh:
            seed = fh.read()
        with open(os.path.join(case_dir, "question.md"), encoding="utf-8") as fh:
            question = fh.read()
        with open(os.path.join(case_dir, "truth.json"), encoding="utf-8") as fh:
            truth = Truth.from_dict(json.load(fh))
        return cls(name=name, path=case_dir, seed=seed, question=question, truth=truth)


# --------------------------------------------------------------------------
# Run config
# --------------------------------------------------------------------------

@dataclass
class FeatureFlags:
    """Per-run feature toggles. The ablation tool flips these one at a time."""
    enable_importance: bool = True
    enable_reflection: bool = True
    enable_contradiction: bool = True
    enable_credibility: bool = True
    enable_conviction: bool = True   # when False, inertia gate is disabled
    bot_pct: float = 0.0
    troll_pct: float = 0.0


@dataclass
class RunConfig:
    """One eval run's inputs."""
    num_agents: int = 20
    num_rounds: int = 10
    seed: int = 1234
    flags: FeatureFlags = field(default_factory=FeatureFlags)


@dataclass
class RunResult:
    """Everything the runner needs to score + persist one run."""
    case: str
    verdict: Verdict
    truth: Truth
    config: RunConfig
    persona_count: int
    reflections_written: int
    conflicts_written: int
    round_posts: List[int] = field(default_factory=list)  # posts per round

    def to_dict(self) -> dict:
        return {
            "case": self.case,
            "verdict": self.verdict.to_dict(),
            "truth": dataclasses.asdict(self.truth),
            "config": {
                "num_agents": self.config.num_agents,
                "num_rounds": self.config.num_rounds,
                "seed": self.config.seed,
                "flags": dataclasses.asdict(self.config.flags),
            },
            "persona_count": self.persona_count,
            "reflections_written": self.reflections_written,
            "conflicts_written": self.conflicts_written,
            "round_posts": self.round_posts,
        }


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def run_case(
    case: DatasetCase,
    *,
    config: Optional[RunConfig] = None,
    router=None,
) -> RunResult:
    """Run a single dataset case and return the scored `RunResult`.

    `router` defaults to a `MockRouter` seeded from `config.seed` — use this
    path in CI / deterministic tests. Pass a live ModelRouter for real runs.
    """
    cfg = config or RunConfig()
    router = router or MockRouter(seed=cfg.seed)
    rng = seeded_random(cfg.seed)

    # 1. Personas
    agent_ids = list(range(cfg.num_agents))
    population = build_population(
        agent_ids=agent_ids,
        bot_pct=cfg.flags.bot_pct,
        troll_pct=cfg.flags.troll_pct,
        rng=seeded_random(cfg.seed + 1),
    )
    persona_gen = PersonaGenerator(router=router, rng=seeded_random(cfg.seed + 2))
    personas: Dict[int, StructuredPersona] = {}
    for agent_id, archetype in sorted(population.assignments.items()):
        if archetype == Archetype.BOT:
            personas[agent_id] = build_bot_persona(
                agent_id=agent_id,
                narrative=f"Mock bot narrative for {case.name}",
            )
        elif archetype == Archetype.TROLL:
            personas[agent_id] = build_troll_persona(agent_id=agent_id)
        else:
            personas[agent_id] = persona_gen.generate(
                agent_id=agent_id,
                entity_name=f"Agent-{agent_id}",
                entity_type=archetype.value,
                topic_summary=case.question,
                archetype=archetype,
            )

    # 2. MemoryManager with Phase-2 / Phase-4 features per flag set.
    manager = MemoryManager(
        simulation_id=f"eval-{case.name}",
        backend=InMemoryBackend(),
        llm_router=router,
        enable_importance=cfg.flags.enable_importance,
        enable_reflection=cfg.flags.enable_reflection,
        enable_contradiction=cfg.flags.enable_contradiction,
    )
    if cfg.flags.enable_credibility:
        manager.set_credibility_weighter(
            CredibilityWeighter(personas, weight=1.0)
        )

    inertia = StanceInertia() if cfg.flags.enable_conviction else None

    # 3. Rounds: each agent may post based on extraversion * random_draw.
    reflections_before = _count_reflections(manager, agent_ids)
    conflicts_before = _count_conflicts(manager, agent_ids)
    round_posts: List[int] = []

    for round_num in range(1, cfg.num_rounds + 1):
        posted_this_round = 0
        # Stable per-round agent order — derived from seed for determinism.
        order = sorted(agent_ids, key=lambda a: (round_num * 131 + a))
        for agent_id in order:
            persona = personas[agent_id]
            extraversion = persona.big_five.extraversion
            draw = rng.random()
            if draw > extraversion:
                continue  # this agent stayed silent this round

            # Build a post whose valence is anchored to the persona's stance,
            # with noise that shrinks as conviction rises.
            noise_amp = max(0.0, 1.0 - persona.conviction) * 0.4
            post_valence = persona.initial_stance.valence + rng.uniform(-noise_amp, noise_amp)
            post_valence = _clamp(post_valence, -1.0, 1.0)

            content = (
                f"[agent-{agent_id} {persona.archetype.value}] "
                f"stance={persona.initial_stance.label} "
                f"valence={post_valence:+.2f}"
            )
            observation = manager.record_agent_action(
                agent_id=agent_id,
                round_num=round_num,
                content=content,
                action_type="CREATE_POST",
                author_id=agent_id,
                public=True,
            )
            # Annotate valence in metadata so the verdict extractor doesn't
            # have to guess from natural-language.
            observation.metadata["valence"] = post_valence
            posted_this_round += 1

            # Record inertia observations from each other agent's POV.
            if inertia is not None:
                for observer_id, observer_persona in personas.items():
                    if observer_id == agent_id:
                        continue
                    inertia.observe_post(
                        observer_agent_id=observer_id,
                        persona=observer_persona,
                        post_valence=post_valence,
                    )

        manager.on_round_complete(round_num)
        round_posts.append(posted_this_round)

    # 4. Verdict + counts.
    verdict = verdict_from_public_timeline(manager, personas=personas)
    reflections_after = _count_reflections(manager, agent_ids)
    conflicts_after = _count_conflicts(manager, agent_ids)

    return RunResult(
        case=case.name,
        verdict=verdict,
        truth=case.truth,
        config=cfg,
        persona_count=len(personas),
        reflections_written=reflections_after - reflections_before,
        conflicts_written=conflicts_after - conflicts_before,
        round_posts=round_posts,
    )


# ---- helpers --------------------------------------------------------------

def _count_reflections(manager: MemoryManager, agent_ids: List[int]) -> int:
    total = 0
    for agent_id in agent_ids:
        total += len(manager.list_reflections(agent_id=agent_id, limit=10_000))
    return total


def _count_conflicts(manager: MemoryManager, agent_ids: List[int]) -> int:
    total = 0
    for agent_id in agent_ids:
        total += len(manager.list_conflicts(agent_id=agent_id, limit=10_000))
    return total


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
