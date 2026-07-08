---
name: add-llm-provider
description: Add a new LLM provider to the client factory. Use when integrating
  any new model API (hosted or local). Covers client, dispatch, catalog,
  capabilities, and API-key wiring.
---
# Add an LLM Provider

1. Subclass `BaseLLMClient` in `tradingagents/llm_clients/<provider>_client.py`.
2. Add to the dispatch in `tradingagents/llm_clients/factory.py`.
3. Add the model list to `tradingagents/llm_clients/model_catalog.py`.
4. Add capability flags to `tradingagents/llm_clients/capabilities.py`
   (structured-output mode, reasoning-effort support). Structured output must
   keep working through `agents/utils/structured.py` — test with a manager node.
5. Add the API key env var to `tradingagents/llm_clients/api_key_env.py`, and a
   placeholder in `tests/conftest.py`.
6. Document the env var in README.md ("Required APIs" section) and
   `.env.example`.
7. Verify: `docker compose run --rm test` (factory + catalog + capabilities
   tests), then one live integration run if you have a key.
