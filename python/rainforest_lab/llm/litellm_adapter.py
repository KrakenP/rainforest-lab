"""LiteLLM reference adapter — turns ``provider/model`` strings into Protocol implementations.

Pulls in ``litellm`` (optional extra: ``pip install rainforest-lab[litellm]``). Covers ~100 LLM
providers behind one interface. Each adapter is a one-liner wrapper around the matching
``make_llm_X`` builder, providing the completion function that calls ``litellm.completion``.

Each provider's "family" is inferred from the slash-prefix of the model string (``openai/...`` →
``openai``, ``anthropic/...`` → ``anthropic``). For the skeptic, callers may override the family
explicitly if their model string doesn't follow the convention."""

from __future__ import annotations

from typing import Any

from rainforest_lab.llm.builders import (
    CompletionFn,
    make_llm_aligner,
    make_llm_gardener,
    make_llm_inspector,
    make_llm_skeptic,
)
from rainforest_lab.llm.protocols import Aligner, Gardener, Inspector, Skeptic


def _require_litellm() -> Any:
    try:
        import litellm  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover — exercised by the missing-dep test
        raise ImportError(
            "litellm is required for the LiteLLM adapter; "
            "install with `pip install rainforest-lab[litellm]`"
        ) from exc
    if litellm is None:  # support monkeypatched-None for tests
        raise ImportError(
            "litellm is required for the LiteLLM adapter; "
            "install with `pip install rainforest-lab[litellm]`"
        )
    return litellm


def _completion_for(model: str, **call_kwargs: Any) -> CompletionFn:
    litellm = _require_litellm()

    def call(system: str, user: str) -> str:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **call_kwargs,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError(f"litellm returned non-string content: {type(content).__name__}")
        return content

    return call


def _infer_family(model: str) -> str:
    """Extract a model family from a ``provider/model`` string. Falls back to the full string."""
    return model.split("/", maxsplit=1)[0].lower() if "/" in model else model.lower()


def litellm_gardener(model: str, **call_kwargs: Any) -> Gardener:
    """Build a gardener backed by ``litellm.completion(model=...)``."""
    return make_llm_gardener(_completion_for(model, **call_kwargs))


def litellm_inspector(model: str, **call_kwargs: Any) -> Inspector:
    return make_llm_inspector(_completion_for(model, **call_kwargs))


def litellm_skeptic(
    model: str, *, model_family: str | None = None, **call_kwargs: Any
) -> Skeptic:
    family = (model_family or _infer_family(model)).lower()
    return make_llm_skeptic(_completion_for(model, **call_kwargs), model_family=family)


def litellm_aligner(model: str, **call_kwargs: Any) -> Aligner:
    return make_llm_aligner(_completion_for(model, **call_kwargs))


__all__ = [
    "litellm_aligner",
    "litellm_gardener",
    "litellm_inspector",
    "litellm_skeptic",
]
