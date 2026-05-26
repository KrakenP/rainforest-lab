import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CYCLE_SCRIPT = ROOT / "skills" / "rainforest-lab" / "scripts" / "rainforest_cycle.py"
VALIDATE_SCRIPT = ROOT / "skills" / "rainforest-lab" / "scripts" / "validate_state.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RainforestCycleTests(unittest.TestCase):
    def test_score_seed_uses_high_potential_weights(self):
        cycle = load_module(CYCLE_SCRIPT, "rainforest_cycle")
        seed = {
            "scores": {
                "novelty": 0.9,
                "logic_strength": 0.8,
                "option_value": 0.7,
                "cross_tree_potential": 0.6,
                "regime_relevance": 0.5,
                "evidence_hint": 0.4,
                "data_availability": 0.3,
                "validation_cost": 0.2,
                "leakage_risk": 0.1,
                "redundancy": 0.0,
            }
        }

        self.assertAlmostEqual(cycle.score_seed(seed), 0.635)

    def test_rank_seeds_quarantines_high_leakage_before_sorting(self):
        cycle = load_module(CYCLE_SCRIPT, "rainforest_cycle")
        seed_bank = {
            "seed_policy": {"seed_slots": 1, "quarantine_leakage_threshold": 0.8},
            "seeds": [
                {
                    "seed_id": "danger",
                    "idea": "Looks exciting but leaks",
                    "scores": {
                        "novelty": 1.0,
                        "logic_strength": 1.0,
                        "option_value": 1.0,
                        "cross_tree_potential": 1.0,
                        "regime_relevance": 1.0,
                        "evidence_hint": 1.0,
                        "data_availability": 1.0,
                        "validation_cost": 0.0,
                        "leakage_risk": 0.9,
                        "redundancy": 0.0,
                    },
                    "validation_plan": "Do not run.",
                },
                {
                    "seed_id": "clean",
                    "idea": "Clean high-potential direction",
                    "scores": {
                        "novelty": 0.7,
                        "logic_strength": 0.7,
                        "option_value": 0.7,
                        "cross_tree_potential": 0.7,
                        "regime_relevance": 0.7,
                        "evidence_hint": 0.7,
                        "data_availability": 0.7,
                        "validation_cost": 0.1,
                        "leakage_risk": 0.1,
                        "redundancy": 0.1,
                    },
                    "validation_plan": "Run a cheap first check.",
                },
            ],
        }

        ranked = cycle.rank_seeds(seed_bank)

        self.assertEqual(ranked[0]["seed_id"], "clean")
        self.assertEqual(ranked[0]["status"], "sow_now")
        self.assertEqual(ranked[1]["seed_id"], "danger")
        self.assertEqual(ranked[1]["status"], "quarantine")

    def test_render_cycle_plan_lists_seed_queue(self):
        cycle = load_module(CYCLE_SCRIPT, "rainforest_cycle")
        ranked = [
            {
                "seed_id": "seed_001",
                "idea": "Explore a boundary condition",
                "seed_score": 0.62,
                "status": "sow_now",
                "validation_plan": "Check a small sample.",
            }
        ]

        plan = cycle.render_cycle_plan(ranked)

        self.assertIn("| 1 | seed_001 | 0.620 | sow_now | Check a small sample. |", plan)


class ValidateStateTests(unittest.TestCase):
    def test_validate_files_accepts_minimal_state_and_seed_bank(self):
        validator = load_module(VALIDATE_SCRIPT, "validate_state")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            forest = tmp_path / "forest.json"
            seeds = tmp_path / "seeds.json"
            forest.write_text(
                json.dumps(
                    {
                        "research_goal": "goal",
                        "domain": "domain",
                        "climate": {},
                        "trees": [],
                    }
                ),
                encoding="utf-8",
            )
            seeds.write_text(
                json.dumps(
                    {
                        "seed_policy": {},
                        "scoring_weights": {},
                        "seeds": [],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(validator.validate_files([forest, seeds]), [])

    def test_cli_reports_missing_required_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            forest = Path(tmp) / "forest.json"
            forest.write_text(json.dumps({"research_goal": "goal"}), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_SCRIPT), str(forest)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required key: domain", result.stdout)


if __name__ == "__main__":
    unittest.main()
