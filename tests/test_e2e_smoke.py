"""End-to-end integration test — requires real LLM API keys. Excluded from CI.

Run manually:
    pytest tests/test_e2e_smoke.py -m integration -v

Uses Anthropic Haiku (lowest cost) for a single full analysis run.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_full_propagate_returns_trade_decision():
    """A complete graph run must produce a final_trade_decision string."""
    import os

    if not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-"):
        pytest.skip("Real ANTHROPIC_API_KEY required for integration test")

    from tradingagents.graph.trading_graph import TradingAgentsGraph

    ta = TradingAgentsGraph(
        debug=False,
        config={
            "llm_provider": "anthropic",
            "deep_think_llm": "claude-haiku-4-5-20251001",
            "quick_think_llm": "claude-haiku-4-5-20251001",
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
        },
    )
    result = ta.propagate("AAPL", "2024-01-15")
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 10
