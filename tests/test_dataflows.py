"""Unit tests for data tool functions — all external calls mocked.

Each tool module does `from tradingagents.dataflows.interface import route_to_vendor`
at import time, binding the name in that module's namespace. We must patch the
name where it's used (the tool module), not where it's defined (interface).
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

_STOCK_VENDOR = "tradingagents.agents.utils.core_stock_tools.route_to_vendor"
_INDICATOR_VENDOR = "tradingagents.agents.utils.technical_indicators_tools.route_to_vendor"
_NEWS_VENDOR = "tradingagents.agents.utils.news_data_tools.route_to_vendor"
_FUNDAMENTAL_VENDOR = "tradingagents.agents.utils.fundamental_data_tools.route_to_vendor"


class TestStockDataTools:
    def test_get_stock_data_passes_args_to_vendor(self):
        from tradingagents.agents.utils.core_stock_tools import get_stock_data

        with patch(_STOCK_VENDOR, return_value="price data") as mock_vendor:
            result = get_stock_data.invoke(
                {"symbol": "AAPL", "start_date": "2024-01-01", "end_date": "2024-01-31"}
            )
        mock_vendor.assert_called_once_with("get_stock_data", "AAPL", "2024-01-01", "2024-01-31")
        assert result == "price data"

    def test_get_indicators_routes_single_indicator(self):
        from tradingagents.agents.utils.technical_indicators_tools import get_indicators

        with patch(_INDICATOR_VENDOR, return_value="rsi data") as mock_vendor:
            result = get_indicators.invoke(
                {"symbol": "AAPL", "indicator": "rsi", "curr_date": "2024-01-15"}
            )
        mock_vendor.assert_called_once_with("get_indicators", "AAPL", "rsi", "2024-01-15", 30)
        assert result == "rsi data"

    def test_get_indicators_splits_comma_separated(self):
        """LLMs sometimes pass multiple indicators; each gets its own vendor call."""
        from tradingagents.agents.utils.technical_indicators_tools import get_indicators

        with patch(_INDICATOR_VENDOR, side_effect=["rsi data", "macd data"]) as mock_vendor:
            result = get_indicators.invoke(
                {"symbol": "AAPL", "indicator": "rsi, macd", "curr_date": "2024-01-15"}
            )
        assert mock_vendor.call_count == 2
        assert "rsi data" in result and "macd data" in result


class TestNewsDataTools:
    def test_get_news_passes_args_to_vendor(self):
        from tradingagents.agents.utils.news_data_tools import get_news

        with patch(_NEWS_VENDOR, return_value="news") as mock_vendor:
            result = get_news.invoke(
                {"ticker": "AAPL", "start_date": "2024-01-01", "end_date": "2024-01-15"}
            )
        mock_vendor.assert_called_once_with("get_news", "AAPL", "2024-01-01", "2024-01-15")
        assert result == "news"

    def test_get_global_news_passes_curr_date(self):
        from tradingagents.agents.utils.news_data_tools import get_global_news

        with patch(_NEWS_VENDOR, return_value="global news") as mock_vendor:
            result = get_global_news.invoke({"curr_date": "2024-01-15"})
        mock_vendor.assert_called_once_with("get_global_news", "2024-01-15", None, None)
        assert result == "global news"

    def test_get_insider_transactions_passes_ticker(self):
        from tradingagents.agents.utils.news_data_tools import get_insider_transactions

        with patch(_NEWS_VENDOR, return_value="insider data") as mock_vendor:
            result = get_insider_transactions.invoke({"ticker": "AAPL"})
        mock_vendor.assert_called_once_with("get_insider_transactions", "AAPL")
        assert result == "insider data"


class TestFundamentalDataTools:
    def test_get_fundamentals_passes_args(self):
        from tradingagents.agents.utils.fundamental_data_tools import get_fundamentals

        with patch(_FUNDAMENTAL_VENDOR, return_value="fundamentals") as mock_vendor:
            result = get_fundamentals.invoke({"ticker": "AAPL", "curr_date": "2024-01-15"})
        mock_vendor.assert_called_once_with("get_fundamentals", "AAPL", "2024-01-15")
        assert result == "fundamentals"

    def test_get_balance_sheet_defaults_to_quarterly(self):
        from tradingagents.agents.utils.fundamental_data_tools import get_balance_sheet

        with patch(_FUNDAMENTAL_VENDOR, return_value="balance sheet") as mock_vendor:
            result = get_balance_sheet.invoke({"ticker": "AAPL"})
        mock_vendor.assert_called_once_with("get_balance_sheet", "AAPL", "quarterly", None)
        assert result == "balance sheet"

    def test_get_cashflow_passes_freq_override(self):
        from tradingagents.agents.utils.fundamental_data_tools import get_cashflow

        with patch(_FUNDAMENTAL_VENDOR, return_value="cashflow") as mock_vendor:
            result = get_cashflow.invoke({"ticker": "AAPL", "freq": "annual"})
        mock_vendor.assert_called_once_with("get_cashflow", "AAPL", "annual", None)
        assert result == "cashflow"

    def test_get_income_statement_returns_vendor_result(self):
        from tradingagents.agents.utils.fundamental_data_tools import get_income_statement

        with patch(_FUNDAMENTAL_VENDOR, return_value="income statement"):
            result = get_income_statement.invoke({"ticker": "AAPL"})
        assert result == "income statement"
