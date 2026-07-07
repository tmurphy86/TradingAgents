"""Unit tests for ConditionalLogic routing — pure function calls, no LLM required."""

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from tradingagents.graph.conditional_logic import ConditionalLogic

pytestmark = pytest.mark.unit


def _ai_msg(content="report text"):
    return AIMessage(content=content)


def _tool_msg():
    return ToolMessage(content="tool result", tool_call_id="call_1")


def _ai_with_tool_calls():
    """AIMessage that carries a pending tool call (triggers tool node)."""
    msg = AIMessage(content="")
    msg.tool_calls = [{"name": "get_stock_data", "args": {}, "id": "call_1"}]
    return msg


# ---------------------------------------------------------------------------
# Analyst routing — routes to tools node OR clear node
# ---------------------------------------------------------------------------


class TestAnalystRouting:
    def setup_method(self):
        self.logic = ConditionalLogic()

    def _state_with(self, msg):
        return {"messages": [msg]}

    def test_market_routes_to_tools_on_tool_call(self):
        state = self._state_with(_ai_with_tool_calls())
        assert self.logic.should_continue_market(state) == "tools_market"

    def test_market_routes_to_clear_on_ai_message(self):
        state = self._state_with(_ai_msg())
        assert self.logic.should_continue_market(state) == "Msg Clear Market"

    def test_social_routes_to_tools_on_tool_call(self):
        state = self._state_with(_ai_with_tool_calls())
        assert self.logic.should_continue_social(state) == "tools_social"

    def test_social_routes_to_clear_on_ai_message(self):
        state = self._state_with(_ai_msg())
        assert self.logic.should_continue_social(state) == "Msg Clear Sentiment"

    def test_news_routes_to_tools_on_tool_call(self):
        state = self._state_with(_ai_with_tool_calls())
        assert self.logic.should_continue_news(state) == "tools_news"

    def test_news_routes_to_clear_on_ai_message(self):
        state = self._state_with(_ai_msg())
        assert self.logic.should_continue_news(state) == "Msg Clear News"

    def test_fundamentals_routes_to_tools_on_tool_call(self):
        state = self._state_with(_ai_with_tool_calls())
        assert self.logic.should_continue_fundamentals(state) == "tools_fundamentals"

    def test_fundamentals_routes_to_clear_on_ai_message(self):
        state = self._state_with(_ai_msg())
        assert self.logic.should_continue_fundamentals(state) == "Msg Clear Fundamentals"


# ---------------------------------------------------------------------------
# Debate routing — round counting and speaker alternation
# ---------------------------------------------------------------------------


def _invest_state(count, current_response=""):
    return {
        "investment_debate_state": {
            "count": count,
            "current_response": current_response,
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "judge_decision": "",
        }
    }


def _risk_state(count, latest_speaker=""):
    return {
        "risk_debate_state": {
            "count": count,
            "latest_speaker": latest_speaker,
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "history": "",
            "judge_decision": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
        }
    }


class TestDebateRouting:
    def setup_method(self):
        self.logic = ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=1)

    def test_debate_routes_to_bear_after_bull(self):
        state = _invest_state(count=1, current_response="Bull: bullish view")
        assert self.logic.should_continue_debate(state) == "Bear Researcher"

    def test_debate_routes_to_bull_after_bear(self):
        state = _invest_state(count=1, current_response="Bear: bearish view")
        assert self.logic.should_continue_debate(state) == "Bull Researcher"

    def test_debate_routes_to_research_manager_at_limit(self):
        state = _invest_state(count=2, current_response="Bull: final")
        assert self.logic.should_continue_debate(state) == "Research Manager"

    def test_debate_respects_max_rounds_config(self):
        logic = ConditionalLogic(max_debate_rounds=2)
        assert logic.should_continue_debate(_invest_state(count=3)) != "Research Manager"
        assert logic.should_continue_debate(_invest_state(count=4)) == "Research Manager"

    def test_risk_routes_to_conservative_after_aggressive(self):
        state = _risk_state(count=1, latest_speaker="Aggressive Analyst")
        assert self.logic.should_continue_risk_analysis(state) == "Conservative Analyst"

    def test_risk_routes_to_neutral_after_conservative(self):
        state = _risk_state(count=2, latest_speaker="Conservative Analyst")
        assert self.logic.should_continue_risk_analysis(state) == "Neutral Analyst"

    def test_risk_routes_to_aggressive_by_default(self):
        state = _risk_state(count=1, latest_speaker="Neutral Analyst")
        assert self.logic.should_continue_risk_analysis(state) == "Aggressive Analyst"

    def test_risk_routes_to_portfolio_manager_at_limit(self):
        state = _risk_state(count=3, latest_speaker="Neutral Analyst")
        assert self.logic.should_continue_risk_analysis(state) == "Portfolio Manager"

    def test_risk_respects_max_rounds_config(self):
        logic = ConditionalLogic(max_risk_discuss_rounds=2)
        assert logic.should_continue_risk_analysis(_risk_state(count=5)) != "Portfolio Manager"
        assert logic.should_continue_risk_analysis(_risk_state(count=6)) == "Portfolio Manager"
