"""Example: write a Gardener against any SDK by implementing the completion function.

This shows how to use the framework's builder (which owns the adversarial prompt + JSON parsing +
family check) with your own LLM client. Use this pattern when LiteLLM doesn't fit (custom auth,
self-hosted models, internal APIs) or when you need provider-specific features.

For ~100 mainstream providers, prefer the LiteLLM adapter:
    from rainforest_lab.llm.litellm_adapter import litellm_gardener
    g = litellm_gardener("openai/gpt-5")
"""

from __future__ import annotations

import os

from rainforest_lab.llm.builders import make_llm_gardener, make_llm_skeptic


def _my_openai_completion(system: str, user: str) -> str:
    """Adapter against the openai SDK. Replace with your real client."""
    try:
        from openai import OpenAI  # pip install openai
    except ImportError:  # pragma: no cover
        raise ImportError("install openai: pip install openai") from None
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    assert isinstance(content, str)
    return content


def _my_anthropic_completion(system: str, user: str) -> str:
    """Adapter against the anthropic SDK."""
    try:
        from anthropic import Anthropic  # pip install anthropic
    except ImportError:  # pragma: no cover
        raise ImportError("install anthropic: pip install anthropic") from None
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


if __name__ == "__main__":
    # Anti-self-favoring: gardener and skeptic must be different model families.
    gardener = make_llm_gardener(_my_openai_completion)
    skeptic = make_llm_skeptic(_my_anthropic_completion, model_family="anthropic")
    # Wire these into the engine via cycle.run_cycle(..., kimi=gardener, skeptic=skeptic, ...).
    print("gardener and skeptic ready (gardener=openai/gpt-5, skeptic=anthropic/claude-opus-4-7)")
