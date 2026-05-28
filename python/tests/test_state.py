from pathlib import Path

from rainforest_lab.state import (
    Branch,
    Climate,
    Forest,
    Seed,
    Tree,
    latest_cycle_dir,
    load_forest,
    save_forest,
)


def _forest() -> Forest:
    return Forest(
        forest_id="rl_test",
        cycle_id="cycle_001",
        research_goal="Find robust alpha",
        domain="demo",
        constraints=["no leakage"],
        approval_policy="manual",
        climate=Climate(
            mode="targeted",
            temperature=0.7,
            seed_budget=0.1,
            seed_slots=2,
            max_tree_share=0.5,
            max_consecutive_depth=3,
            novelty_weight=0.2,
        ),
        data_soil={"ready": True},
        trees=[
            Tree(
                tree_id="tree_1",
                name="Tree One",
                core_logic="simple mechanism",
                status="active",
                recent_budget_share=0.25,
                branches=[
                    Branch(
                        branch_id="branch_1",
                        parent=None,
                        depth=1,
                        hypothesis="rank(x)",
                        status="proposed",
                        cycle_executed=None,
                        result_classification=None,
                    )
                ],
            )
        ],
        seeds=[
            Seed(
                seed_id="seed_1",
                idea="try a monotone transform",
                source_type="manual",
                related_trees=["tree_1"],
                scores={"novelty": 0.7},
                seed_score=0.7,
                status="hold",
                validation_plan="evaluate once data is ready",
                reason="promising but not urgent",
            )
        ],
        summary="test forest",
    )


def test_forest_yaml_roundtrip(tmp_path: Path) -> None:
    forest = _forest()

    save_forest(forest, tmp_path)
    loaded = load_forest(tmp_path)

    assert loaded.forest_id == forest.forest_id
    assert loaded.trees[0].branches[0].hypothesis == "rank(x)"
    assert loaded.seeds[0].seed_id == "seed_1"
    assert loaded.climate.max_tree_share == 0.5


def test_latest_cycle_dir(tmp_path: Path) -> None:
    (tmp_path / "cycle_000").mkdir()
    (tmp_path / "cycle_002").mkdir()

    assert latest_cycle_dir(tmp_path) == tmp_path / "cycle_002"
