from __future__ import annotations

from typing import NoReturn

from rainforest_lab.domain import gate_record_complete
from rainforest_lab.errors import RainforestError
from rainforest_lab.state import Forest, GateDef, ResultRecord


class ForestValidationError(RainforestError):
    """Fail-loud validator error."""


def validate_forest(forest: Forest, gate_spec: list[GateDef] | None = None) -> None:
    for result in forest.results:
        _validate_result(result, gate_spec)

    for event in forest.weather_events:
        if not event.reason.strip():
            _fail(
                "WeatherEvent.reason must be non-empty",
                invariant="c",
                target=event.target,
                weather=event.weather,
            )

    _validate_allocations(forest)
    _validate_branch_depths(forest)


def _validate_result(result: ResultRecord, gate_spec: list[GateDef] | None) -> None:
    if result.execution_mode is None:
        _fail(
            "ResultRecord.execution_mode is required",
            invariant="d",
            result_id=result.result_id,
        )

    if result.execution_mode == "stub_result" and result.classification == "fruit":
        _fail(
            "stub_result can never be classified as fruit",
            invariant="b",
            result_id=result.result_id,
        )

    if result.classification == "fruit":
        if result.execution_mode != "tool_executed":
            _fail(
                "fruit requires execution_mode='tool_executed'",
                invariant="a",
                result_id=result.result_id,
                execution_mode=result.execution_mode,
            )
        if result.gate_record is None:
            _fail("fruit requires gate_record", invariant="a", result_id=result.result_id)
        if gate_spec is None:
            complete = result.gate_record.complete
        else:
            complete = gate_record_complete(result.gate_record, gate_spec)
        if not complete:
            _fail(
                "fruit requires complete gate_record",
                invariant="a",
                result_id=result.result_id,
                factor_id=result.gate_record.factor_id,
            )
        if result.gate_record.execution_mode != "tool_executed":
            _fail(
                "fruit gate_record requires execution_mode='tool_executed'",
                invariant="a",
                result_id=result.result_id,
                factor_id=result.gate_record.factor_id,
                execution_mode=result.gate_record.execution_mode,
            )

    if result.classification == "sick_leaf" and not result.blocked_from_reuse:
        _fail(
            "sick_leaf records must be blocked_from_reuse",
            invariant="g",
            result_id=result.result_id,
        )


def _validate_allocations(forest: Forest) -> None:
    total_allocation = sum(event.allocation for event in forest.weather_events)
    if total_allocation > 1.0:
        _fail(
            "tree allocations must sum to <= 1.0",
            invariant="e",
            allocation=total_allocation,
        )

    by_target: dict[str, float] = {}
    for event in forest.weather_events:
        if event.target_type == "tree":
            by_target[event.target] = by_target.get(event.target, 0.0) + event.allocation

    for tree in forest.trees:
        allocation = by_target.get(tree.tree_id, tree.recent_budget_share)
        if allocation > forest.climate.max_tree_share:
            _fail(
                "tree allocation exceeds climate.max_tree_share",
                invariant="e",
                tree_id=tree.tree_id,
                allocation=allocation,
                max_tree_share=forest.climate.max_tree_share,
            )


def _validate_branch_depths(forest: Forest) -> None:
    for tree in forest.trees:
        for branch in tree.branches:
            if branch.depth > forest.climate.max_consecutive_depth:
                _fail(
                    "branch depth exceeds climate.max_consecutive_depth",
                    invariant="f",
                    tree_id=tree.tree_id,
                    branch_id=branch.branch_id,
                    depth=branch.depth,
                    max_consecutive_depth=forest.climate.max_consecutive_depth,
                )


def _fail(message: str, **context: object) -> NoReturn:
    raise ForestValidationError(message, context=context)


__all__ = ["ForestValidationError", "validate_forest"]
