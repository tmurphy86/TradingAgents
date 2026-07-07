"""Smoke tests for TradingAgentsGraph — verifies graph compiles without LLM calls."""

import pytest

pytestmark = pytest.mark.smoke


def test_graph_compiles(mock_llm_client):
    """Graph must compile cleanly: all nodes registered, edges wired, no import errors."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    ta = TradingAgentsGraph(debug=False)
    assert ta.graph is not None


def test_graph_has_required_attributes(mock_llm_client):
    """Core attributes that the API and CLI rely on must be present after init."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    ta = TradingAgentsGraph(debug=False)
    assert hasattr(ta, "graph")
    assert hasattr(ta, "propagator")
    assert hasattr(ta, "signal_processor")
    assert hasattr(ta, "memory_log")


def test_graph_config_overrides_applied(mock_llm_client):
    """A config dict merged onto DEFAULT_CONFIG must be respected."""
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    cfg = {**DEFAULT_CONFIG, "max_debate_rounds": 2}
    ta = TradingAgentsGraph(debug=False, config=cfg)
    assert ta.config["max_debate_rounds"] == 2
