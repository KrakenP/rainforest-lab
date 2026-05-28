import pytest

from rainforest_lab.state import (
    Branch,
    Climate,
    Forest,
    GateRecord,
    ResultRecord,
    Seed,
    Tree,
    WeatherEvent,
)
from rainforest_lab.validate import ForestValidationError, validate_forest


def _valid_forest() -> Forest:
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
                recent_budget_share=0.4,
                branches=[
                    Branch(
                        branch_id="branch_1",
                        parent=None,
                        depth=1,
                        hypothesis="rank(x)",
                        status="classified",
                        cycle_executed=1,
                        result_classification="fruit",
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
        weather_events=[
            WeatherEvent(
                target="tree_1",
                target_type="tree",
                weather="rain",
                allocation=0.4,
                reason="best current path",
            )
        ],
        results=[
            ResultRecord(
                result_id="result_1",
                task_id="task_1",
                execution_mode="tool_executed",
                classification="fruit",
                summary="all gates passed",
                classification_reason="complete evidence",
                gate_record=GateRecord(
                    domain="demo",
                    factor_id="factor_1",
                    gates={"g1": {"passed": True, "response": "ok"}},
                    execution_mode="tool_executed",
                ),
            )
        ],
        summary="test forest",
    )


def test_fruit_requires_complete_tool_executed_gate_record() -> None:
    forest = _valid_forest()
    forest.results[0].gate_record = GateRecord(
        domain="demo",
        factor_id="factor_1",
        gates={},
        execution_mode="tool_executed",
    )

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_stub_result_can_never_be_fruit() -> None:
    forest = _valid_forest()
    forest.results[0].execution_mode = "stub_result"

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_weather_event_reason_non_empty() -> None:
    forest = _valid_forest()
    forest.weather_events[0].reason = ""

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_result_record_requires_execution_mode() -> None:
    forest = _valid_forest()
    forest.results[0].execution_mode = None  # type: ignore[assignment]

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_tree_allocations_within_budget_and_tree_cap() -> None:
    forest = _valid_forest()
    forest.weather_events[0].allocation = 0.7

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_branch_depth_within_climate_limit() -> None:
    forest = _valid_forest()
    forest.trees[0].branches[0].depth = 4

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_sick_leaf_records_block_reuse() -> None:
    forest = _valid_forest()
    forest.results[0].classification = "sick_leaf"
    forest.results[0].blocked_from_reuse = False

    with pytest.raises(ForestValidationError):
        validate_forest(forest)


def test_valid_forest_passes() -> None:
    validate_forest(_valid_forest())
