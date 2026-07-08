# tradingagents/ — Pipeline, Agents, LLM Clients

## Key files

```
graph/trading_graph.py      TradingAgentsGraph (entry point); _WATCHED_FIELDS / _DEBATE_FIELDS drive SSE diffing
graph/setup.py              builds the LangGraph StateGraph (node chain + routing)
graph/conditional_logic.py  all routing decisions (should_continue_* functions)
graph/reflection.py         Reflector — scores past decisions against realized returns
agents/utils/agent_states.py AgentState (TypedDict, the full graph state)
agents/utils/memory.py      TradingMemoryLog (append-only decision log + pending-entry reflection)
agents/utils/structured.py  provider-specific structured-output binding
agents/schemas.py           Pydantic output models (ResearchPlan, TraderProposal, PortfolioDecision)
llm_clients/factory.py      create_llm_client() dispatch to all providers
llm_clients/capabilities.py capability flags (structured-output mode, reasoning-effort support)
default_config.py           DEFAULT_CONFIG + TRADINGAGENTS_* env overrides (_ENV_OVERRIDES)
```

## Rules

- **Messages are cleared between phases.** `create_msg_delete()` wipes `AgentState.messages` after each analyst completes. Intentional — do not remove when adding agents.
- **Debate counts are doubled/tripled.** Investment debate alternates Bull → Bear (`max_debate_rounds=1` → 2 calls). Risk debate cycles three agents (`max_risk_discuss_rounds=1` → 3 calls).
- **Structured output only via `agents/utils/structured.py`.** Never assume `response_format` or `tool_choice` — the helper respects the provider capability matrix.
- **Check `capabilities.py` flags** before passing `reasoning_effort` / `thinking` kwargs to any model call.
- **Crypto mode skips fundamentals.** `asset_type="crypto"` excludes the fundamentals analyst via `graph/analyst_execution.py` — check it when adding crypto-aware agents.
- **Config precedence:** programmatic config dict > `TRADINGAGENTS_*` env vars (declared in `_ENV_OVERRIDES` with type coercion) > `DEFAULT_CONFIG`.
- New analyst or LLM provider? Use the `add-analyst` / `add-llm-provider` skills — they carry the full checklists.
- If a new analyst report field should stream to the dashboard, add it to `_WATCHED_FIELDS` in `graph/trading_graph.py`.
