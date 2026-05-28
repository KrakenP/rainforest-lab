import pytest

from rainforest_lab.roles import ROLES, role


def test_known_roles() -> None:
    expected = {
        "gardener",
        "inspector",
        "diverger",
        "aligner",
        "meteorologist",
        "examiner",
        "coordinator",
        "skeptic",
    }

    assert expected <= set(ROLES)
    for name in expected:
        assert role(name) == ROLES[name]


def test_unknown_role_raises() -> None:
    with pytest.raises(KeyError):
        role("unknown")
