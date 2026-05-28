from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd

import rainforest_lab.handoff as handoff_adapter
from rainforest_lab import events, seeds, weather
from rainforest_lab.classify import classify as classify_record
from rainforest_lab.deliberation import (
    DeliberationConfig,
    ParallelGardenersConfig,
    deliberate_tree,
)
from rainforest_lab.domain import ResearchDomain
from rainforest_lab.llm.protocols import Gardener, Inspector, Judgment, Mechanism, Skeptic
from rainforest_lab.roles import role
from rainforest_lab.state import (
    Branch,
    Forest,
    GateRecord,
    ResultRecord,
    Seed,
    WeatherEvent,
    save_forest,
)
from rainforest_lab.validate import validate_forest

DEFAULT_HANDOFF_TIMEOUT_S = 1800


def run_cycle(
    forest: Forest,
    domain: ResearchDomain,
    *,
    archive_root: Path,
    kimi: Gardener,
    deepseek: Inspector,
    handoff: Any = handoff_adapter,
    skeptic: Skeptic | None = None,
    deliberation: DeliberationConfig | None = None,
    parallel: ParallelGardenersConfig | None = None,
) -> Forest:
    """Advance one canonical rainforest cycle and persist the next archive snapshot.

    With ``deliberation is None`` the v1 single-pass research runs verbatim. When a
    ``DeliberationConfig`` is supplied, the coordinator dispatches one gardener per allocated tree
    and runs the v2.0 bounded gardener-skeptic deliberation, merging per-tree results in a
    deterministic tree_id-sorted order. The coordinator stays the only forest-state writer.
    """

    gate_spec = domain.gate_spec()
    validate_forest(forest, gate_spec)

    archive_root = Path(archive_root)
    events_path = archive_root / "events.jsonl"
    current_cycle = _cycle_number(forest.cycle_id)
    next_cycle = current_cycle + 1
    next_cycle_id = f"cycle_{next_cycle:03d}"
    next_forest = forest.model_copy(deep=True, update={"cycle_id": next_cycle_id})

    _emit(
        events_path,
        "coordinator",
        "validate_pre",
        forest.cycle_id,
        {"cycle_id": forest.cycle_id},
        {"ok": True},
        "pre-cycle validator passed before any rainforest state mutation.",
        current_cycle,
    )

    forest_weather = weather.route(
        forest,
        current_cycle,
        total_fruits=_promoted_count(forest),
        streaks=_streaks(forest),
        last_alloc=_last_allocations(forest),
        data_ready=domain.data_readiness(),
        climate=forest.climate,
    )
    _apply_weather(next_forest, forest_weather)
    _emit(
        events_path,
        "meteorologist",
        "route",
        forest.cycle_id,
        {"tree_count": len(forest.trees), "cycle": current_cycle},
        {
            "trigger_kimi": forest_weather.trigger_kimi,
            "trigger_monsoon": forest_weather.trigger_monsoon,
            "trees": {
                tree_id: _public_dict(event)
                for tree_id, event in forest_weather.trees.items()
            },
        },
        "weather.route assigned tree weather and seed-slot pressure for this cycle.",
        current_cycle,
    )

    if deliberation is None:
        _run_v1_research(
            next_forest,
            forest_weather,
            domain,
            kimi,
            deepseek,
            handoff,
            events_path,
            current_cycle,
            next_cycle_id,
        )
    else:
        if skeptic is None:
            raise ValueError("v2 deliberation requires a skeptic adapter (no silent fallback)")
        _run_deliberation(
            next_forest,
            forest,
            domain,
            forest_weather,
            parallel or ParallelGardenersConfig(),
            deliberation,
            kimi,
            deepseek,
            skeptic,
            handoff,
            events_path,
            current_cycle,
        )

    next_forest.summary = _cycle_summary(next_forest, next_cycle)
    validate_forest(next_forest, gate_spec)
    save_forest(next_forest, archive_root / next_cycle_id)
    _emit(
        events_path,
        "coordinator",
        "validate_post_save",
        next_cycle_id,
        {"cycle_id": next_cycle_id},
        {"ok": True, "result_count": len(next_forest.results)},
        "post-cycle validator passed and the next forest snapshot was archived.",
        next_cycle,
    )
    return next_forest


def _run_v1_research(
    next_forest: Forest,
    forest_weather: weather.ForestWeather,
    domain: ResearchDomain,
    kimi: Any,
    deepseek: Any,
    handoff: Any,
    events_path: Path,
    current_cycle: int,
    next_cycle_id: str,
) -> None:
    """v1 single-pass research (unchanged): mine once -> diverge -> seeds -> nursery -> evaluate."""

    mechanisms: list[Mechanism] = []
    if forest_weather.trigger_kimi or not _has_sowable_seed(next_forest):
        mechanisms = _mine_mechanisms(next_forest, domain, kimi, events_path, current_cycle)
        divergent = _request_divergence(
            mechanisms,
            next_forest,
            handoff,
            events_path,
            current_cycle,
        )
        mechanism_seeds = _mechanisms_to_seeds(
            mechanisms,
            divergent,
            next_forest,
            deepseek,
            events_path,
            current_cycle,
        )
        next_forest.seeds.extend(mechanism_seeds)

    next_forest.seeds = seeds.rank_and_route(
        next_forest.seeds,
        slots=next_forest.climate.seed_slots,
    )
    _emit(
        events_path,
        "coordinator",
        "rank_and_route_seeds",
        next_cycle_id,
        {"seed_count": len(next_forest.seeds), "slots": next_forest.climate.seed_slots},
        {"routed": [_seed_summary(seed) for seed in next_forest.seeds]},
        "seed bank was scored and routed before nursery checks.",
        current_cycle,
    )

    tasks = _build_candidate_tasks(next_forest, events_path, current_cycle)
    for task in tasks:
        record = _evaluate_task(
            task,
            next_forest,
            domain,
            handoff,
            events_path,
            current_cycle,
        )
        next_forest.results.append(record)
        _apply_result_to_tree(next_forest, task, record)
        _retire_evaluated_seed(next_forest, str(task["seed_id"]), record.classification)


def _run_deliberation(
    next_forest: Forest,
    forest: Forest,
    domain: ResearchDomain,
    forest_weather: weather.ForestWeather,
    parallel: ParallelGardenersConfig,
    config: DeliberationConfig,
    kimi: Any,
    deepseek: Any,
    skeptic: Any,
    handoff: Any,
    events_path: Path,
    current_cycle: int,
) -> None:
    """v2.0 coordinator: dispatch one gardener per allocated tree, merge deterministically.

    The coordinator is the single writer. ``deliberate_tree`` is pure (reads ``next_forest``,
    returns candidate data); results merge in tree_id-sorted order so the cycle is reproducible.
    """

    allocated = _allocated_trees(next_forest, forest_weather)
    temps = parallel.temperature_spread or (1.0,)
    dispatch = {tree.tree_id: temps[idx % len(temps)] for idx, tree in enumerate(allocated)}
    _emit(
        events_path,
        "coordinator",
        "gardener_parallel_dispatch",
        next_forest.cycle_id,
        {"trees": [tree.tree_id for tree in allocated], "max_concurrent": parallel.max_concurrent},
        {"dispatch": dispatch},
        "coordinator dispatched one gardener per allocated tree for parallel deliberation.",
        current_cycle,
    )

    promoted_pool = _promoted_pool(forest)
    for tree in allocated:
        result = deliberate_tree(
            tree,
            next_forest,
            domain,
            temperature=dispatch[tree.tree_id],
            config=config,
            gardener=kimi,
            skeptic=skeptic,
            deepseek=deepseek,
            handoff=handoff,
            events_path=events_path,
            cycle=current_cycle,
            promoted_pool=promoted_pool,
        )
        next_forest.seeds.extend(result.seeds)
        for task, record in result.records:
            next_forest.results.append(record)
            _apply_result_to_tree(next_forest, task, record)
            _retire_evaluated_seed(next_forest, str(task["seed_id"]), record.classification)


def _allocated_trees(
    forest: Forest, forest_weather: weather.ForestWeather
) -> list[Any]:
    allocated_ids = {
        tree_id
        for tree_id, event in forest_weather.trees.items()
        if getattr(event, "allocation", 0) > 0
    }
    trees = [tree for tree in forest.trees if tree.tree_id in allocated_ids]
    if not trees:
        trees = [tree for tree in forest.trees if tree.status == "active"]
    return sorted(trees, key=lambda tree: tree.tree_id)


def _mine_mechanisms(
    forest: Forest,
    domain: ResearchDomain,
    kimi: Any,
    events_path: Path,
    cycle: int,
) -> list[Mechanism]:
    active_logic = "; ".join(tree.core_logic for tree in forest.trees if tree.status == "active")
    mechanisms: list[Mechanism] = kimi.mine(
        active_logic or forest.research_goal,
        domain.feature_space(),
        _taboos(forest),
        _explored(forest),
        max(1, forest.climate.seed_slots),
    )
    _emit(
        events_path,
        "gardener",
        "mine",
        forest.cycle_id,
        {"feature_space": domain.feature_space().__dict__},
        {"mechanisms": [_public_dict(mechanism) for mechanism in mechanisms]},
        "Kimi gardener mined mechanisms because routing requested fresh candidate seeds.",
        cycle,
    )
    return mechanisms


def _request_divergence(
    mechanisms: list[Mechanism],
    forest: Forest,
    handoff: Any,
    events_path: Path,
    cycle: int,
) -> list[dict[str, Any]]:
    schema = {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "formula": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["formula"],
                    "additionalProperties": True,
                },
            }
        },
        "additionalProperties": True,
    }
    response = handoff.request(
        "divergence",
        {"mechanisms": [_public_dict(mechanism) for mechanism in mechanisms]},
        schema,
        req_id=f"{forest.cycle_id}-divergence",
        timeout_s=DEFAULT_HANDOFF_TIMEOUT_S,
    )
    candidates = response.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    result = [candidate for candidate in candidates if isinstance(candidate, dict)]
    _emit(
        events_path,
        "diverger",
        "handoff_divergence",
        forest.cycle_id,
        {"mechanism_count": len(mechanisms)},
        {"candidate_count": len(result), "candidates": result},
        "Claude divergence handoff returned schema-bounded alternative candidates.",
        cycle,
    )
    return result


def _mechanisms_to_seeds(
    mechanisms: list[Mechanism],
    divergent: list[dict[str, Any]],
    forest: Forest,
    deepseek: Any,
    events_path: Path,
    cycle: int,
) -> list[Seed]:
    seeds_out: list[Seed] = []
    tree_id = _active_tree_id(forest)
    used_ids = {seed.seed_id for seed in forest.seeds}
    for idx, mechanism in enumerate(mechanisms, start=1):
        judgment: Judgment = deepseek.judge(mechanism)
        _emit(
            events_path,
            "inspector",
            "judge",
            mechanism.name,
            {"mechanism": _public_dict(mechanism)},
            {"judgment": _public_dict(judgment)},
            "DeepSeek inspector judged mechanism consistency, novelty, and leakage risk.",
            cycle,
        )
        seed_id = _unique_id(f"seed_{forest.cycle_id}_{idx}", used_ids)
        seeds_out.append(
            Seed(
                seed_id=seed_id,
                idea=mechanism.intuition,
                source_type="kimi",
                related_trees=[tree_id] if tree_id else [],
                scores=_scores_from_judgment(judgment),
                status="hold",
                validation_plan=_formula_from_text(mechanism.pseudocode),
                reason=f"{mechanism.name}: {judgment.concerns}",
            )
        )
    for idx, candidate in enumerate(divergent, start=1):
        seed_id = _unique_id(f"seed_{forest.cycle_id}_div_{idx}", used_ids)
        formula = str(candidate.get("formula", "")).strip()
        seeds_out.append(
            Seed(
                seed_id=seed_id,
                idea=str(candidate.get("name") or candidate.get("reason") or formula),
                source_type="handoff_divergence",
                related_trees=[tree_id] if tree_id else [],
                scores={
                    "novelty": 0.75,
                    "logic_strength": 0.70,
                    "option_value": 0.60,
                    "cross_tree_potential": 0.30,
                    "regime_relevance": 0.50,
                    "evidence_hint": 0.40,
                    "data_availability": 1.0,
                    "validation_cost": 0.25,
                    "leakage_risk": 0.0,
                    "redundancy": 0.10,
                },
                status="hold",
                validation_plan=_formula_from_text(formula),
                reason=str(candidate.get("reason") or "divergence handoff candidate"),
            )
        )
    return seeds_out


def _build_candidate_tasks(
    forest: Forest,
    events_path: Path,
    cycle: int,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for seed in forest.seeds:
        if seed.status != "sow_now":
            continue
        nursery = seeds.nursery_check(seed, forest)
        _emit(
            events_path,
            "coordinator",
            "nursery_check",
            seed.seed_id,
            {"seed": _seed_summary(seed)},
            {"decision": _public_dict(nursery)},
            "nursery applied seven bounded checks before candidate execution.",
            cycle,
        )
        if nursery.decision != "sprout":
            seed.status = nursery.decision  # type: ignore[assignment]
            seed.reason = nursery.reason
            seed.validation_plan = nursery.next_validation
            continue
        tasks.append(
            {
                "task_id": f"task_{forest.cycle_id}_{len(tasks) + 1:03d}",
                "seed_id": seed.seed_id,
                "tree_id": seed.related_trees[0] if seed.related_trees else _active_tree_id(forest),
                "formula": seed.validation_plan,
                "mechanism": seed.idea,
                "execution_mode": "tool_executed",
            }
        )
    return tasks


def _evaluate_task(
    task: dict[str, Any],
    forest: Forest,
    domain: ResearchDomain,
    handoff: Any,
    events_path: Path,
    cycle: int,
) -> ResultRecord:
    compiled = domain.compile_candidate(str(task["formula"]))
    gate_record = domain.evaluate(
        compiled,
        run_id=str(task["task_id"]),
        promoted_pool=_promoted_pool(forest),
    )
    _emit(
        events_path,
        "examiner",
        "evaluate",
        str(task["task_id"]),
        {"task": task},
        {"gate_record": gate_record.model_dump(mode="json")},
        "domain examiner evaluated the compiled candidate with the domain gate battery.",
        cycle,
    )

    align = domain.align_request(
        gate_record.factor_id,
        str(task["mechanism"]),
        {"gates": gate_record.gates, "formula": task["formula"]},
    )
    g7_response = handoff.request(
        "g7_alignment",
        {"rubric": align.rubric, "request": _public_dict(align)},
        align.schema,
        req_id=f"{forest.cycle_id}-{task['task_id']}-g7",
        timeout_s=DEFAULT_HANDOFF_TIMEOUT_S,
    )
    _merge_alignment(gate_record, g7_response)
    _emit(
        events_path,
        "aligner",
        "handoff_g7_alignment",
        gate_record.factor_id,
        {"factor_id": gate_record.factor_id, "mechanism": task["mechanism"]},
        g7_response,
        "Claude G7 alignment handoff scored mechanism-evidence alignment.",
        cycle,
    )

    classification, reason = classify_record(gate_record, domain.gate_spec())
    _emit(
        events_path,
        "coordinator",
        "classify",
        gate_record.factor_id,
        {"gate_record": gate_record.model_dump(mode="json")},
        {"classification": classification, "reason": reason},
        "complete gate evidence was classified into rainforest result taxonomy.",
        cycle,
    )
    return ResultRecord(
        result_id=f"result_{task['task_id']}",
        task_id=str(task["task_id"]),
        execution_mode="tool_executed",
        classification=classification,
        summary=f"{task['formula']} classified as {classification}",
        classification_reason=reason,
        blocked_from_reuse=classification == "sick_leaf",
        gate_record=gate_record,
    )


def _apply_weather(forest: Forest, routed: weather.ForestWeather) -> None:
    slots = max(1, sum(max(event.allocation, 0) for event in routed.trees.values()))
    for tree in forest.trees:
        event = routed.trees.get(tree.tree_id)
        if event is None:
            continue
        share = min(float(event.allocation) / float(slots), forest.climate.max_tree_share)
        tree.status = event.status  # type: ignore[assignment]
        tree.recent_budget_share = share
    forest.weather_events = [
        WeatherEvent(
            target=event.tree_id,
            target_type="tree",
            weather=event.weather,
            allocation=min(float(event.allocation) / float(slots), forest.climate.max_tree_share),
            reason=event.reason,
        )
        for event in routed.trees.values()
    ]


def _apply_result_to_tree(forest: Forest, task: dict[str, Any], result: ResultRecord) -> None:
    tree = next((item for item in forest.trees if item.tree_id == task.get("tree_id")), None)
    if tree is None:
        return
    depth = min(_next_branch_depth(tree), forest.climate.max_consecutive_depth)
    branch = Branch(
        branch_id=f"branch_{task['task_id']}",
        parent=None,
        depth=depth,
        hypothesis=str(task["formula"]),
        status="classified",
        cycle_executed=_cycle_number(forest.cycle_id),
        result_classification=result.classification,
        evidence_summary=result.summary,
        blocks_reuse=result.blocked_from_reuse,
    )
    tree.branches.append(branch)

    if result.classification == "fruit":
        tree.status = "active"
        tree.weather_priors["moisture"] = 1.0
        tree.weather_priors["clear_next_validation"] = True
        for seed in forest.seeds:
            if seed.status == "hold" and tree.tree_id in seed.related_trees:
                seed.status = "sow_now"
                break
    elif result.classification == "golden_leaf":
        child_id = f"{branch.branch_id}_child"
        branch.child_branches_proposed.append(child_id)
        tree.branches.append(
            Branch(
                branch_id=child_id,
                parent=branch.branch_id,
                depth=min(depth + 1, forest.climate.max_consecutive_depth),
                hypothesis=f"refine {task['formula']}",
                status="proposed",
            )
        )
    elif result.classification == "sick_leaf":
        tree.status = "frost"
        forest.sick_leaf_warnings.append(
            {
                "tree_id": tree.tree_id,
                "result_id": result.result_id,
                "reason": result.classification_reason,
                "blocked_from_reuse": True,
            }
        )
    elif result.classification == "dead_leaf":
        tree.weather_priors["drought"] = 1.0


def _retire_evaluated_seed(forest: Forest, seed_id: str, classification: str | None) -> None:
    """Quarantine a seed after gate evaluation so it is not re-evaluated next cycle.

    Seeds that pass (fruit) stay sow_now so the next hold seed can be promoted.
    Every other classification means the seed is done — quarantine prevents rank_and_route
    from re-promoting it to sow_now in subsequent cycles.
    """
    if classification == "fruit":
        return
    for seed in forest.seeds:
        if seed.seed_id == seed_id:
            seed.status = "quarantine"
            break


def _merge_alignment(gate_record: GateRecord, response: dict[str, Any]) -> None:
    score = response.get("score")
    passed = isinstance(score, int | float) and float(score) >= 1.0
    payload = {**response, "passed": passed}
    if "alignment" in gate_record.gates:
        gate_record.gates["alignment"].update(payload)
    gate_record.gates["G7"] = payload


def _promoted_pool(forest: Forest) -> dict[str, pd.Series]:
    return {}


def _promoted_count(forest: Forest) -> int:
    return sum(1 for result in forest.results if result.classification == "fruit")


def _streaks(forest: Forest) -> dict[str, Any]:
    streaks: dict[str, Any] = {}
    if forest.results and not any(result.classification == "fruit" for result in forest.results):
        streaks["_forest_no_output"] = 1
    for tree in forest.trees:
        classified = [
            branch.result_classification
            for branch in tree.branches
            if branch.result_classification
        ]
        if not classified:
            continue
        zero = 0 if "fruit" in classified else len(classified)
        dead = sum(1 for item in classified if item == "dead_leaf")
        streaks[tree.tree_id] = {"zero": zero, "dead": dead}
    return streaks


def _last_allocations(forest: Forest) -> dict[str, Any]:
    return {
        event.target: _cycle_number(forest.cycle_id)
        for event in forest.weather_events
        if event.target_type == "tree" and event.allocation > 0
    }


def _has_sowable_seed(forest: Forest) -> bool:
    return any(seed.status in {"sow_now", "hold"} for seed in forest.seeds)


def _taboos(forest: Forest) -> list[str]:
    taboos = [warning.get("reason", "") for warning in forest.sick_leaf_warnings]
    return [str(item) for item in taboos if str(item).strip()]


def _explored(forest: Forest) -> list[str]:
    return [branch.hypothesis for tree in forest.trees for branch in tree.branches]


def _active_tree_id(forest: Forest) -> str:
    for tree in forest.trees:
        if tree.status == "active":
            return tree.tree_id
    return forest.trees[0].tree_id if forest.trees else ""


def _next_branch_depth(tree: Any) -> int:
    if not tree.branches:
        return 1
    return int(max(branch.depth for branch in tree.branches)) + 1


def _scores_from_judgment(judgment: Judgment) -> dict[str, float]:
    cost = {"low": 0.2, "medium": 0.5, "high": 0.9}.get(judgment.validation_cost.lower(), 0.5)
    return {
        "novelty": float(judgment.novelty_score),
        "logic_strength": 1.0 if judgment.logic_consistent else 0.0,
        "option_value": min(max(float(judgment.alignment_score) / 3.0, 0.0), 1.0),
        "cross_tree_potential": 0.3,
        "regime_relevance": 0.5,
        "evidence_hint": 0.5,
        "data_availability": 1.0,
        "validation_cost": cost,
        "leakage_risk": 1.0 if judgment.lookahead_detected else 0.0,
        "redundancy": 0.1,
    }


def _formula_from_text(text: str) -> str:
    """Extract a single DSL expression from pseudocode (may be multi-line with assignments)."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("candidate formula must be non-empty")
    lines = [ln.strip() for ln in re.split(r'[;\n]', stripped) if ln.strip()]
    if len(lines) == 1:
        m = re.match(r'^[A-Za-z_]\w*\s*=\s*(.+)$', lines[0])
        return m.group(1).strip() if m else lines[0]
    # Multi-statement (newline or semicolon-separated): inline assignments, return last expression
    env: dict[str, str] = {}
    last_expr = stripped
    for line in lines:
        m = re.match(r'^([A-Za-z_]\w*)\s*=\s*(.+)$', line)
        if m:
            varname, rhs = m.group(1), m.group(2).strip()
            env[varname] = _substitute_vars(rhs, env)
            last_expr = env[varname]
        else:
            last_expr = _substitute_vars(line, env)
    return last_expr


def _substitute_vars(expr: str, env: dict[str, str]) -> str:
    for name in sorted(env, key=len, reverse=True):
        expr = re.sub(rf'\b{re.escape(name)}\b', env[name], expr)
    return expr


def _unique_id(prefix: str, used_ids: set[str]) -> str:
    candidate = prefix
    idx = 1
    while candidate in used_ids:
        idx += 1
        candidate = f"{prefix}_{idx}"
    used_ids.add(candidate)
    return candidate


def _seed_summary(seed: Seed) -> dict[str, Any]:
    return {
        "seed_id": seed.seed_id,
        "status": seed.status,
        "seed_score": seed.seed_score,
        "related_trees": seed.related_trees,
        "execution_mode": "tool_executed" if seed.status == "sow_now" else "plan_only",
    }


def _cycle_summary(forest: Forest, cycle: int) -> str:
    return (
        f"cycle {cycle}: {len(forest.results)} total results, "
        f"{_promoted_count(forest)} promoted fruits"
    )


def _cycle_number(cycle_id: str) -> int:
    try:
        return int(cycle_id.rsplit("_", maxsplit=1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"cycle_id must look like cycle_000, got {cycle_id!r}") from exc


def _public_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        data = item.model_dump(mode="json")
        return data if isinstance(data, dict) else {"value": data}
    if is_dataclass(item):
        data = asdict(cast(Any, item))
        return data if isinstance(data, dict) else {"value": data}
    if hasattr(item, "__dict__"):
        return dict(item.__dict__)
    return {"value": item}


def _emit(
    events_path: Path,
    role_name: str,
    action: str,
    target: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reason: str,
    cycle: int,
) -> None:
    events.emit(
        "Codex",
        role_name,
        action,
        target,
        inputs=inputs,
        outputs=outputs,
        reason=f"{role(role_name)}: {reason}",
        cycle=cycle,
        events_path=events_path,
    )


__all__ = ["run_cycle"]
