# TradingAgents — Multi-Agent Trading Research & Execution Platform

**From market analysis to risk-defined trades — a multi-agent LLM pipeline with a quant ensemble, structured trade construction (equities + defined-risk options), and policy-gated execution that graduates from paper to live only when the evidence says so.**

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> ⚠️ **This is a personal research system, not investment advice.** It informs and (in paper mode) executes trades for its owner's account. LLM-driven signals are non-deterministic and vulnerable to regime change; backtest results do not guarantee live performance. See [Safety model](#safety-model).

Built on the open-source [TradingAgents](https://github.com/TauricResearch/TradingAgents) framework by [Tauric Research](https://tauric.ai/) ([arXiv:2412.20138](https://arxiv.org/abs/2412.20138)) — see [Origins & attribution](#origins--attribution).

---

## What this is

The original TradingAgents framework mirrors a trading firm: analyst agents (market, sentiment, news, fundamentals) feed structured bull/bear and risk debates, and a portfolio manager issues a BUY/HOLD/SELL rating. This project extends that research framework into an end-to-end personal trading platform:

1. **Analyze** — the 12-agent LLM pipeline, streamed live to a web dashboard, with full deep-dive access to every report, debate transcript, and data source behind each decision.
2. **Quantify** — a deterministic quant layer (momentum, mean reversion, volatility, valuation) ensembled with the LLM verdict into a 0–100 conviction score. Disagreement between the two is surfaced, not averaged away.
3. **Construct** — ranked, risk-defined trade ideas instead of a bare rating: entry zone, stop, targets, position size, risk/reward, invalidation — for equities and defined-risk options strategies (spreads, covered calls, CSPs). Every number is computed; the LLM chooses and explains.
4. **Measure** — a reflection loop scores every decision against realized returns; an accuracy dashboard tracks hit rate and alpha vs SPY by ticker, sector, and methodology (ensemble vs LLM-only vs quant-only).
5. **Execute (gated)** — a deterministic policy engine (conviction threshold, trailing-accuracy floor, risk caps, loss breaker, blackout windows) submits orders through a broker adapter, on a strict safety ladder: **paper → live with human confirmation → live auto**, each stage earned by soak evidence, never scheduled.

A macro regime screener (rates, curve, VIX, breadth × per-sector system accuracy) directs the run budget toward sectors where the system actually wins, and watchlists carry schedule/macro/event triggers to launch analyses automatically within budget guards.

## Status

| Capability | Status |
|---|---|
| 12-agent LangGraph pipeline, 13 LLM providers, structured outputs | ✅ Shipped |
| Web dashboard: live SSE runs, history, watchlists | ✅ Shipped |
| Reflection loop (decisions scored vs realized returns) | ✅ Shipped |
| GCP Cloud Run deployment, CI/CD (GitHub Actions + WIF), Terraform | ✅ Shipped |
| Per-run cost tracking, run cancellation, parallel analysts | 🚧 Phase 1 |
| Accuracy dashboard + point-in-time backtest harness | 🚧 Phase 2 |
| Quant ensemble, TradeIdea construction, options strategies | 🔜 Phase 3 |
| Macro regime screener, deep-dive AI explain, settings/policy UI | 🔜 Phase 3 |
| Policy-gated execution (Alpaca paper → confirm → auto) | 🔒 Phase 4, gated |

Roadmap and workstreams: [docs/IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) · UI mockups for the new screens: [docs/ui-samples.html](docs/ui-samples.html)

## Safety model

Execution is treated as the most dangerous feature in the system, and is engineered accordingly:

- **No LLM in the execution path.** Models propose; only validated, typed `TradeIdea` objects cross into `tradingagents/execution/`, where deterministic code decides and submits.
- **Policy engine as the only gate.** Conviction threshold, per-ticker trailing-accuracy floor, per-trade and portfolio risk caps, daily-loss circuit breaker, earnings blackout, and a degraded-data block — every rejection logged with the failing rule. Hard bounds are enforced in code; the UI cannot exceed them.
- **Staged ladder.** Paper trading (≥4-week clean soak) → live with per-order human confirmation → live auto per trade-type, promoted only by soak-report review. Live and paper credentials are separate secrets; mode is explicit config.
- **Defined-risk options only.** No naked short options, ever. Liquidity filters (OI, volume, spread) before any strategy is proposed.
- **Kill switch.** One action cancels all open orders and halts the policy engine; triggered automatically by the loss breaker or reconciliation mismatch.

## Quick start

### Web dashboard (recommended)

```bash
cp .env.example .env      # add your API keys
docker compose up api
# open http://localhost:8080
```

Configure a run → watch 12 agents stream live → review the decision, then drill into the full analysis.

### Interactive CLI

```bash
uv sync --extra api       # install (uv: pip install uv / brew install uv)
tradingagents             # or: python -m cli.main
```

Docker CLI: `docker compose run --rm tradingagents` · local models: `docker compose --profile ollama run --rm tradingagents-ollama`

### Python

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"          # 13 providers: openai, anthropic, google, xai, deepseek, qwen[-cn], glm[-cn], minimax[-cn], openrouter, ollama, azure
config["deep_think_llm"] = "gpt-5.4"       # research + portfolio manager
config["quick_think_llm"] = "gpt-5.4-mini" # everyone else
config["max_debate_rounds"] = 1

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

Real-time events: pass `event_callback=fn` to `propagate()`. All options: `tradingagents/default_config.py`.

### API keys

Set the key for your chosen LLM provider plus `ALPHA_VANTAGE_API_KEY` for fundamentals data — full list in [.env.example](.env.example). Enterprise providers (Azure OpenAI, Bedrock): `.env.enterprise.example`. Local models: set `llm_provider: "ollama"` (default endpoint `http://localhost:11434/v1`, override with `OLLAMA_BASE_URL`).

## Architecture

**Pipeline:** Market → Sentiment → News → Fundamentals analysts → Bull ↔ Bear debate → Research Manager → Trader → Aggressive/Conservative/Neutral risk debate → Portfolio Manager → *(Phase 3)* quant ensemble → trade construction → *(Phase 4)* policy gate → broker.

**Analyst team** — fundamentals (financials, intrinsic value), sentiment (StockTwits/Reddit/news mood), news (macro + company events), technicals (MACD, RSI, trend structure). **Researcher team** — bull and bear agents debate the analyst evidence; a research manager rules. **Trader + risk team** — a trader drafts the transaction; aggressive/conservative/neutral risk agents stress it; the portfolio manager issues the final rating.

```
tradingagents/   LangGraph pipeline, agents, LLM clients, (soon) quant/ + execution/
api/             FastAPI backend: run management, SSE streaming, watchlists
ui/              React + Vite + Tailwind dashboard
terraform/       GCP infra (Cloud Run, GCS, Secret Manager, Artifact Registry, WIF)
.github/workflows/  CI (lint, security, tests, AI review) + deploy + terraform plan/apply
```

**Persistence** (all under `~/.tradingagents/`, GCS FUSE on Cloud Run): append-only decision log with reflections (`memory/trading_memory.md`), per-ticker checkpoint DBs for crash resume (opt-in `--checkpoint`), run records, watchlists. Override paths via `TRADINGAGENTS_*` env vars.

## Deploy to GCP

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # project_id, github_owner, invoker_email
terraform init && terraform apply
echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-   # then add to active_secrets, re-apply
```

After the initial image push, every merge to `main` tests, builds, and deploys automatically via GitHub Actions (Workload Identity Federation — no service-account keys). The service is IAM-authenticated with zero idle cost. Full guide: [docs/OVERVIEW.md](docs/OVERVIEW.md#gcp-deployment).

## Testing

```bash
docker compose run --rm test                     # unit + smoke + regression, same container as CI
python -m pytest tests/ -m "unit or smoke" -q    # quick local run
```

Markers: `unit` · `smoke` · `regression` (API/SSE, mocked) · `integration` (live providers). Details: [tests/CLAUDE.md](tests/CLAUDE.md).

## Documentation

- [docs/OVERVIEW.md](docs/OVERVIEW.md) — full technical reference: configuration, architecture, repository map, agent catalog, persistence, deployment
- [docs/IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) — product direction, workstreams, phased roadmap, success criteria
- [docs/ui-samples.html](docs/ui-samples.html) — interactive mockups of the nine dashboard screens (open in a browser)
- [docs/CLAUDE_CONFIG_PLAN.md](docs/CLAUDE_CONFIG_PLAN.md) — AI-assisted development setup (subagents, skills, hooks)
- [CHANGELOG.md](CHANGELOG.md) — release history (v0.2.5: grounded sentiment analyst, GPT-5.5 coverage, env-var configurability, ticker-path hardening)

## Origins & attribution

This project is a fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents), the multi-agent LLM trading framework by Yijia Xiao, Edward Sun, Di Luo, and Wei Wang. The agent pipeline, debate architecture, and research foundations are their work; this fork adds the production platform (web dashboard, API, GCP deployment), the quant ensemble and trade-construction direction, and the gated execution layer. The upstream framework is designed for research purposes — that spirit carries over here: [not financial, investment, or trading advice](https://tauric.ai/disclaimer/).

If this work helps you, please cite the original paper:

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138},
}
```

## License

See [LICENSE](LICENSE). Contributions and issue reports are welcome; contributor credits per release in [CHANGELOG.md](CHANGELOG.md).
