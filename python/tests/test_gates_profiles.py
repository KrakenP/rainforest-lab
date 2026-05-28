from __future__ import annotations

from pathlib import Path

import pytest

from rainforest_lab.gates.profiles import load_gates_profile


def test_load_gates_profile_returns_callables(tmp_path: Path) -> None:
    yaml_path = tmp_path / "profile.yaml"
    yaml_path.write_text(
        """
net_sharpe: {fee_bp: 8.54, periods_per_year: 12}
g1_sanity:  {nan_max: 0.30}
g5_turnover: {turnover_max: 0.40}
g8_decay:    {max_decay_slope: 0.0}
g9_liquidity:
  min_adv: 100000.0
""",
        encoding="utf-8",
    )
    profile = load_gates_profile(yaml_path)
    assert callable(profile["net_sharpe"])
    assert callable(profile["g1_sanity"])
    assert callable(profile["g5_turnover"])
    assert callable(profile["g8_decay"])
    assert callable(profile["g9_liquidity"])


def test_load_gates_profile_rejects_unknown_gate(tmp_path: Path) -> None:
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text("frobnicate_3000: {x: 1}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frobnicate_3000"):
        load_gates_profile(yaml_path)
