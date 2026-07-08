---
name: add-analyst
description: Add a new analyst node to the trading pipeline. Use when creating
  any new analyst agent (market, sentiment, news, fundamentals, custom).
  Covers node registration, state fields, routing, and dashboard streaming.
---
# Add an Analyst

1. Create `tradingagents/agents/analysts/<name>.py` — return a string report;
   tool-calling or pre-loaded data.
2. Register the node in `tradingagents/graph/setup.py` (node chain +
   conditional routing).
3. Add the report field to `AgentState` in
   `tradingagents/agents/utils/agent_states.py`.
4. Tool-calling analyst? Add a `should_continue_*` function in
   `tradingagents/graph/conditional_logic.py`.
5. Add the field to `_WATCHED_FIELDS` in `tradingagents/graph/trading_graph.py`
   so the dashboard streams it live.
6. Crypto-aware? Check the exclusion list in
   `tradingagents/graph/analyst_execution.py` (crypto mode skips fundamentals).
7. Add the step to the `PIPELINE` constant in `ui/src/pages/RunPage.tsx` if it
   should appear as a dashboard step.
8. Verify: `docker compose run --rm test`, then a manual run watching
   `/runs/:id` — the new report must stream live.

Do NOT remove `create_msg_delete()` message clearing when wiring the node.
