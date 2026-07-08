# dataflows/ — Data Vendors

- `interface.py` routes between vendors (yfinance / alpha_vantage); reddit + stocktwits feed the sentiment analyst.
- **Ticker validation blocks path traversal.** `utils.py` sanitises tickers before they are used in file paths. Apply it to EVERY new file write — no exceptions.
- Alpha Vantage free tier is heavily rate-limited; batch and cache where possible.
- Vendor failures must never silently degrade an analyst report — raise or flag, don't return empty strings (see IMPROVEMENT_PLAN.md Agent E: shared fetch wrapper + degraded-run flag).
- Keep vendor modules self-contained; the graph layer must import only through `interface.py`.
