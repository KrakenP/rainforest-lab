from pathlib import Path

from rainforest_lab.seeds import (
    DEFAULT_CONFIG_PATH,
    nursery_check,
    rank_and_route,
    score_seed,
    set_config_path,
)
from rainforest_lab.state import Climate, Forest, Seed, Tree


def _seed(seed_id: str, scores: dict[str, float], **overrides: object) -> Seed:
    data = {
        "seed_id": seed_id,
        "idea": "test idea",
        "source_type": "manual",
        "related_trees": ["t1"],
        "scores": scores,
        "status": "hold",
        "validation_plan": "evaluate with holdout",
        "reason": "candidate",
    }
    data.update(overrides)
    return Seed(**data)  # type: ignore[arg-type]


def _forest() -> Forest:
    return Forest(
        forest_id="rl",
        cycle_id="cycle_001",
        research_goal="Find alpha",
        domain="demo",
        approval_policy="manual",
        climate=Climate(
            mode="exploration",
            temperature=1.0,
            seed_budget=0.25,
            seed_slots=3,
            max_tree_share=0.50,
            max_consecutive_depth=2,
            novelty_weight=0.35,
        ),
        data_soil={"ready": True},
        trees=[Tree(tree_id="t1", name="t1", core_logic="mechanism", status="active")],
        summary="test",
    )


def test_score_seed_formula() -> None:
    scores = {
        "novelty": 1.0,
        "logic_strength": 0.5,
        "option_value": 0.4,
        "cross_tree_potential": 0.2,
        "regime_relevance": 0.3,
        "evidence_hint": 0.6,
        "data_availability": 1.0,
        "validation_cost": 0.2,
        "leakage_risk": 0.1,
        "redundancy": 0.5,
    }

    assert score_seed(scores) == 0.48


def test_high_leakage_quarantined() -> None:
    seeds = [_seed("leaky", {"novelty": 1.0, "leakage_risk": 0.9})]

    routed = rank_and_route(seeds, slots=1)

    assert routed[0].status == "quarantine"


def test_top_slots_sown() -> None:
    seeds = [
        _seed("low", {"novelty": 0.1}),
        _seed("high", {"novelty": 1.0}),
        _seed("mid", {"novelty": 0.5}),
    ]

    routed = rank_and_route(seeds, slots=2)

    assert [seed.seed_id for seed in routed[:2]] == ["high", "mid"]
    assert [seed.status for seed in routed] == ["sow_now", "sow_now", "hold"]


def test_nursery_7_checks() -> None:
    forest = _forest()
    sprout = _seed(
        "sprout",
        {
            "novelty": 0.9,
            "logic_strength": 0.8,
            "data_availability": 1.0,
            "leakage_risk": 0.1,
            "redundancy": 0.1,
            "validation_cost": 0.2,
        },
    )
    leaky = _seed("leaky", {"leakage_risk": 0.95})
    missing_data = _seed("missing", {"data_availability": 0.1})
    duplicate = _seed("dupe", {"novelty": 0.2, "redundancy": 0.95})

    assert nursery_check(sprout, forest).decision == "sprout"
    assert nursery_check(leaky, forest).decision == "quarantine"
    assert nursery_check(missing_data, forest).decision == "dormant"
    assert nursery_check(duplicate, forest).decision == "reject"
    assert "7 checks" in nursery_check(sprout, forest).reason


def test_set_config_path_loads_custom_weights(tmp_path: Path) -> None:
    custom = tmp_path / "custom.yaml"
    # Heavily weight `novelty` and zero everything else so 1.0 novelty -> score == 1.0
    custom.write_text(
        "seed_scoring_weights:\n"
        "  novelty: 1.0\n"
        "  logic_strength: 0.0\n"
        "  option_value: 0.0\n"
        "  cross_tree_potential: 0.0\n"
        "  regime_relevance: 0.0\n"
        "  evidence_hint: 0.0\n"
        "  data_availability: 0.0\n"
        "  validation_cost: 0.0\n"
        "  leakage_risk: 0.0\n"
        "  redundancy: 0.0\n",
        encoding="utf-8",
    )
    try:
        set_config_path(custom)
        assert score_seed({"novelty": 1.0}) == 1.0
    finally:
        set_config_path(DEFAULT_CONFIG_PATH)
