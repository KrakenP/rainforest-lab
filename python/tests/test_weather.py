from rainforest_lab.state import Branch, Climate, Forest, Tree
from rainforest_lab.weather import route


def _climate() -> Climate:
    return Climate(
        mode="exploration",
        temperature=1.0,
        seed_budget=0.25,
        seed_slots=3,
        max_tree_share=0.50,
        max_consecutive_depth=2,
        novelty_weight=0.35,
    )


def _branch(branch_id: str, classification: str, *, depth: int = 1) -> Branch:
    return Branch(
        branch_id=branch_id,
        depth=depth,
        parent=None,
        hypothesis="rank(x)",
        status="classified",
        result_classification=classification,  # type: ignore[arg-type]
    )


def _tree(
    tree_id: str,
    branches: list[Branch] | None = None,
    *,
    status: str = "active",
    priors: dict[str, object] | None = None,
) -> Tree:
    return Tree(
        tree_id=tree_id,
        name=tree_id,
        core_logic="mechanism",
        status=status,  # type: ignore[arg-type]
        branches=branches or [],
        weather_priors=priors or {},
    )


def _forest(trees: list[Tree]) -> Forest:
    return Forest(
        forest_id="rl",
        cycle_id="cycle_001",
        research_goal="Find alpha",
        domain="demo",
        approval_policy="manual",
        climate=_climate(),
        trees=trees,
        summary="test",
    )


def test_every_event_has_reason() -> None:
    forest = _forest([_tree("t1"), _tree("t2", [_branch("b1", "fruit")])])

    routed = route(
        forest,
        1,
        total_fruits=1,
        streaks={},
        last_alloc={},
        data_ready={},
        climate=forest.climate,
    )

    assert routed.trees
    assert all(event.reason.strip() for event in routed.trees.values())


def test_max_tree_share_capped() -> None:
    forest = _forest(
        [
            _tree("winner", [_branch(f"f{i}", "fruit") for i in range(10)]),
            _tree("other"),
        ]
    )

    routed = route(
        forest,
        2,
        total_fruits=10,
        streaks={},
        last_alloc={},
        data_ready={},
        climate=forest.climate,
    )

    assert routed.trees["winner"].allocation <= 2
    assert sum(event.allocation for event in routed.trees.values()) <= 4


def test_depth_cap_forces_diversity() -> None:
    forest = _forest(
        [
            _tree("deep", [_branch("b1", "fruit", depth=2)]),
            _tree("shallow"),
        ]
    )

    routed = route(
        forest,
        3,
        total_fruits=1,
        streaks={},
        last_alloc={},
        data_ready={},
        climate=forest.climate,
    )

    assert routed.trees["deep"].allocation <= 1
    assert routed.trees["shallow"].allocation >= 1


def test_frost_recheck_interval() -> None:
    forest = _forest([_tree("frosted", status="frost"), _tree("active")])

    waiting = route(
        forest,
        4,
        total_fruits=0,
        streaks={},
        last_alloc={},
        data_ready={"frosted": True},
        climate=forest.climate,
    )
    thawed = route(
        forest,
        5,
        total_fruits=0,
        streaks={},
        last_alloc={},
        data_ready={"frosted": True},
        climate=forest.climate,
    )

    assert waiting.trees["frosted"].weather == "frost"
    assert waiting.trees["frosted"].allocation == 0
    assert thawed.trees["frosted"].weather == "spring"
    assert thawed.trees["frosted"].allocation >= 1


def test_monsoon_triggers_kimi() -> None:
    forest = _forest([_tree("t1"), _tree("t2")])

    routed = route(
        forest,
        7,
        total_fruits=0,
        streaks={},
        last_alloc={},
        data_ready={},
        climate=forest.climate,
    )

    assert routed.trigger_monsoon
    assert routed.trigger_kimi
    assert any(event.weather == "monsoon" for event in routed.trees.values())


def test_thunderstorm_freezes_and_triggers_kimi() -> None:
    forest = _forest([_tree("bad", [_branch(f"d{i}", "dead_leaf") for i in range(3)]), _tree("ok")])

    routed = route(
        forest,
        8,
        total_fruits=0,
        streaks={"bad": {"zero": 3, "dead": 3}},
        last_alloc={},
        data_ready={},
        climate=forest.climate,
    )

    assert routed.trees["bad"].weather == "thunderstorm"
    assert routed.trees["bad"].status == "frozen"
    assert routed.trees["bad"].freeze_remaining == 2
    assert routed.trigger_kimi


def test_flood_diversity_tax() -> None:
    forest = _forest(
        [
            _tree("dominant", [_branch(f"f{i}", "fruit") for i in range(5)]),
            _tree("minor"),
        ]
    )

    routed = route(
        forest,
        9,
        total_fruits=5,
        streaks={},
        last_alloc={},
        data_ready={},
        climate=forest.climate,
    )

    assert routed.trees["dominant"].weather == "flood"
    assert routed.trees["minor"].allocation >= 1
