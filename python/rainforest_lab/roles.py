from __future__ import annotations

ROLES = {
    "gardener": "hypothesis miner (LLM) - plants seeds",
    "inspector": "pre-nursery judge (LLM)",
    "diverger": "Claude/host divergence (handoff)",
    "aligner": "Claude/host G7 alignment (handoff)",
    "meteorologist": "weather router",
    "examiner": "gate evaluator (domain)",
    "coordinator": "cycle orchestrator + forest bookkeeping",
    "skeptic": "red-team critic (different model family) - challenges hypotheses/fruit-candidates",
}


def role(name: str) -> str:
    return ROLES[name]


__all__ = ["ROLES", "role"]
