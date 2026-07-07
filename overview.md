# TradingAgents — Overview

TradingAgents is a multi-agent AI framework for producing structured stock and crypto trading recommendations. It chains four data-gathering analysts, a bull/bear debate, a risk debate, and a portfolio manager into a single LangGraph workflow that terminates with a five-tier investment rating.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [LLM Providers](#llm-providers)
5. [Architecture Overview](#architecture-overview)
6. [Repository Map](#repository-map)
7. [Agent Catalog](#agent-catalog)
8. [Data Sources](#data-sources)
9. [Persistence & Recovery](#persistence--recovery)
10. [GCP Deployment](#gcp-deployment)
11. [Key Extension Points](#key-extension-points)

---

## What It Does

Given a ticker symbol and a trade date, the system:

1. Runs four parallel analyst agents to gather technical, sentiment, news, and fundamental data.
2. Runs a structured bull/bear debate to surface investment arguments.
3. Synthesizes a `ResearchPlan` (Buy → Sell, 5-tier) via a Research Manager.
4. Converts that plan into a concrete `TraderProposal` (Buy/Hold/Sell with entry price, stop-loss, position sizing).
5. Runs an aggressive/conservative/neutral risk debate.
6. Emits a final `PortfolioDecision` from the Portfolio Manager, including a price target, time horizon, and executive summary.

All outputs are Pydantic-validated structured objects, rendered to markdown for logging and display.

---

## Quick Start

### Install

```bash
git clone <repo>
cd TradingAgents
uv sync --extra api
```

Copy `.env.example` to `.env` and fill in at least one provider API key.

### Web Dashboard (recommended)

```bash
cp .env.example .env
docker compose up api
# open http://localhost:8080
```

The dashboard lets you configure and launch analysis runs, watch all 12 agent steps stream in real time, review history, and manage watchlists.

### CLI (interactive terminal)

```bash
tradingagents
```

The CLI walks through: provider → models → ticker → date → asset type → analysts → debate rounds.

### Programmatic

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["deep_think_llm"] = "gpt-5.4"
config["quick_think_llm"] = "gpt-5.4-mini"

ta = TradingAgentsGraph(debug=True, config=config)
final_state, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

### Docker (CLI only)

```bash
cp .env.example .env
docker compose run --rm tradingagents

# With local Ollama
docker compose --profile ollama run --rm tradingagents-ollama
```

---

## Configuration

### Primary config file: `tradingagents/default_config.py`

All keys have defaults and can be overridden with `TRADINGAGENTS_*` environment variables.

| Config Key | Env Var | Default | Notes |
|---|---|---|---|
| `llm_provider` | `TRADINGAGENTS_LLM_PROVIDER` | `openai` | Provider name |
| `deep_think_llm` | `TRADINGAGENTS_DEEP_THINK_LLM` | `gpt-5.4` | Manager agents |
| `quick_think_llm` | `TRADINGAGENTS_QUICK_THINK_LLM` | `gpt-5.4-mini` | Analyst/researcher agents |
| `backend_url` | `TRADINGAGENTS_LLM_BACKEND_URL` | — | Custom endpoint (Ollama, proxy) |
| `max_debate_rounds` | `TRADINGAGENTS_MAX_DEBATE_ROUNDS` | `1` | Bull/bear cycles |
| `max_risk_discuss_rounds` | `TRADINGAGENTS_MAX_RISK_ROUNDS` | `1` | Agg/cons/neu cycles |
| `online_tools` | — | `true` | Toggle live data fetching |
| `data_provider` | — | `yfinance` | `yfinance` or `alpha_vantage` |
| `output_language` | `TRADINGAGENTS_OUTPUT_LANGUAGE` | `English` | All agent outputs |
| `checkpoint_enabled` | `TRADINGAGENTS_CHECKPOINT_ENABLED` | `false` | SQLite checkpoint/resume |
| `benchmark_ticker` | `TRADINGAGENTS_BENCHMARK_TICKER` | `SPY` | Alpha benchmark |

Programmatic overrides take the highest precedence; env vars override defaults; the `DEFAULT_CONFIG` dict is the fallback.

### API Keys

```
OPENAI_API_KEY          OpenAI
ANTHROPIC_API_KEY       Anthropic / Claude
GOOGLE_API_KEY          Google Gemini
XAI_API_KEY             xAI / Grok
DEEPSEEK_API_KEY        DeepSeek
DASHSCOPE_API_KEY       Qwen (international)
DASHSCOPE_CN_API_KEY    Qwen (China region)
ZHIPU_API_KEY           GLM / Z.AI (international)
ZHIPU_CN_API_KEY        GLM / BigModel (China region)
MINIMAX_API_KEY         MiniMax (global)
MINIMAX_CN_API_KEY      MiniMax (China region)
OPENROUTER_API_KEY      OpenRouter aggregator
OLLAMA_BASE_URL         Remote Ollama server URL
ALPHA_VANTAGE_API_KEY   Alpha Vantage data
```

---

## LLM Providers

| Provider | Key Models | Notes |
|---|---|---|
| OpenAI | GPT-5.5, GPT-5.4, GPT-5.4-mini, GPT-4.1 | Default; structured output via `json_schema` |
| Anthropic | Claude Opus 4.7/4.6, Sonnet 4.6, Haiku 4.5 | Structured output via tool_choice |
| Google | Gemini 3.1 Flash/Pro, Gemini 2.0, 1.5 | Structured output via response_schema |
| xAI | Grok 4.20, Grok 2 | OpenAI-compatible endpoint |
| DeepSeek | DeepSeek-R1, DeepSeek-V4 | Reasoning models |
| Qwen | Qwen 3.6/3.5/3 Plus/Flash/Max | Dual-region (intl + China) |
| GLM | GLM-5.1, GLM-5, GLM-4.7, GLM-4.5-Air | Dual-region (Z.AI + BigModel) |
| MiniMax | M2.7, M2.5, M2.1 (highspeed) | 204K context; dual-region |
| OpenRouter | Any model via aggregator | Single API key for many backends |
| Ollama | Any local model | Local or remote via `OLLAMA_BASE_URL` |

Each provider has a capability matrix in `tradingagents/llm_clients/capabilities.py` that controls which structured-output mode and reasoning-effort parameters are used.

---

## Architecture Overview

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  ANALYST PHASE  (quick_think_llm, data-gathering)        │
│                                                          │
│  Market Analyst ──► Sentiment Analyst ──► News Analyst   │
│                              └──────────► Fundamentals   │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  INVESTMENT DEBATE PHASE  (quick_think_llm)              │
│                                                          │
│  Bull Researcher ◄──► Bear Researcher  (N rounds)        │
│                              │                           │
│                    Research Manager (deep_think_llm)     │
│                              │                           │
│                       ResearchPlan (5-tier rating)       │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  TRADER  (quick_think_llm)                               │
│                                                          │
│  TraderProposal: action + entry + stop-loss + sizing     │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  RISK DEBATE PHASE  (quick_think_llm)                    │
│                                                          │
│  Aggressive ──► Conservative ──► Neutral  (N rounds)     │
│                              │                           │
│                    Portfolio Manager (deep_think_llm)    │
│                              │                           │
│                    PortfolioDecision (5-tier rating)     │
└─────────────────────────────────────────────────────────┘
  │
  ▼
END  →  final_trade_decision (string) + full AgentState
```

### State Object (`AgentState`)

The LangGraph state (`tradingagents/agents/utils/agent_states.py`) carries everything between nodes:

```python
company_of_interest     # ticker symbol
asset_type              # "stock" | "crypto"
trade_date              # YYYY-MM-DD

market_report           # str from Market Analyst
sentiment_report        # str from Sentiment Analyst
news_report             # str from News Analyst
fundamentals_report     # str from Fundamentals Analyst

investment_debate_state # InvestDebateState (history + round count)
investment_plan         # str (ResearchPlan rendered to markdown)
trader_investment_plan  # str (TraderProposal rendered to markdown)
risk_debate_state       # RiskDebateState (history + round count)
final_trade_decision    # str (PortfolioDecision rendered to markdown)

past_context            # str (injected memory-log entries from prior runs)
messages                # LangGraph MessagesState (cleared between phases)
```

### Debate Routing

`conditional_logic.py` controls flow:
- Analyst nodes loop on tool calls until no more tool calls remain, then proceed.
- Investment debate: Bull → Bear alternates until `round_count >= 2 × max_debate_rounds`, then routes to Research Manager.
- Risk debate: Agg → Cons → Neu cycles until `round_count >= 3 × max_risk_discuss_rounds`, then routes to Portfolio Manager.
- Messages are cleared between phases to avoid context bloat.

---

## Repository Map

```
TradingAgents/
├── main.py                          # Minimal programmatic entry point
├── pyproject.toml                   # Package metadata and dependencies (v0.2.5)
├── Dockerfile                       # CLI image (interactive terminal, uv-based)
├── docker-compose.yml               # CLI + API services; ollama profile
├── cloudbuild.yaml                  # GCP CI/CD pipeline (test → build → push → deploy)
├── .env.example                     # API key template
│
├── api/                             # FastAPI backend + web dashboard server
│   ├── main.py                      # Run management, SSE streaming, watchlist CRUD, StaticFiles mount
│   └── Dockerfile                   # 3-stage build: Node (UI) → uv/Python (deps) → slim runtime
│
├── ui/                              # React + Vite + Tailwind web dashboard
│   ├── src/
│   │   ├── api.ts                   # fetch-based API client; streamRun() → EventSource
│   │   ├── types.ts                 # RunRequest, RunRecord, RunResult, Watchlist interfaces
│   │   ├── App.tsx                  # BrowserRouter + routes
│   │   ├── components/Layout.tsx    # Fixed sidebar navigation
│   │   └── pages/
│   │       ├── NewRunPage.tsx       # Run configuration form
│   │       ├── RunPage.tsx          # Live SSE agent pipeline view
│   │       ├── HistoryPage.tsx      # Past runs table
│   │       └── WatchlistsPage.tsx   # Watchlist manager
│   ├── package.json                 # React 18, react-router-dom 6, Tailwind 3, Vite 5
│   └── vite.config.ts               # /api proxy → :8080 in dev; outputs to dist/
│
├── terraform/                       # Infrastructure as Code for GCP
│   ├── main.tf                      # Provider config + optional GCS backend
│   ├── variables.tf                 # All input variables with defaults
│   ├── outputs.tf                   # Cloud Run URL, bucket name, example curl command
│   ├── apis.tf                      # Enables required GCP APIs
│   ├── iam.tf                       # Service account + all IAM bindings
│   ├── storage.tf                   # GCS bucket (mounts as ~/.tradingagents in Cloud Run)
│   ├── secrets.tf                   # Secret Manager stubs for all provider API keys
│   ├── registry.tf                  # Artifact Registry Docker repository
│   ├── run.tf                       # Cloud Run v2 service (GCS mount, secret env vars)
│   ├── build.tf                     # Cloud Build trigger on push to main
│   └── terraform.tfvars.example     # Variable values template (copy → terraform.tfvars)
│
│
├── tradingagents/                   # Core Python package
│   ├── default_config.py            # DEFAULT_CONFIG + env-var override system
│   │
│   ├── graph/                       # LangGraph workflow
│   │   ├── trading_graph.py         # TradingAgentsGraph: main class, entry point
│   │   ├── setup.py                 # GraphSetup: builds and compiles StateGraph
│   │   ├── propagation.py           # Propagator: initializes AgentState
│   │   ├── conditional_logic.py     # ConditionalLogic: routing between nodes
│   │   ├── analyst_execution.py     # Execution planning + concurrency
│   │   ├── reflection.py            # Reflector: outcome reflection / memory update
│   │   ├── checkpointer.py          # SQLite checkpoint / resume
│   │   └── signal_processing.py     # Extracts decision from final report
│   │
│   ├── agents/                      # Agent implementations
│   │   ├── schemas.py               # Pydantic output models (ResearchPlan, TraderProposal, PortfolioDecision)
│   │   ├── analysts/
│   │   │   ├── market_analyst.py
│   │   │   ├── sentiment_analyst.py
│   │   │   ├── news_analyst.py
│   │   │   └── fundamentals_analyst.py
│   │   ├── researchers/
│   │   │   ├── bull_researcher.py
│   │   │   └── bear_researcher.py
│   │   ├── managers/
│   │   │   ├── research_manager.py
│   │   │   └── portfolio_manager.py
│   │   ├── risk_mgmt/
│   │   │   ├── aggressive_debator.py
│   │   │   ├── conservative_debator.py
│   │   │   └── neutral_debator.py
│   │   ├── trader/
│   │   │   └── trader.py
│   │   └── utils/
│   │       ├── agent_states.py           # AgentState, InvestDebateState, RiskDebateState
│   │       ├── agent_utils.py            # Language instructions, tool definitions, instrument context
│   │       ├── memory.py                 # TradingMemoryLog (decision log)
│   │       ├── structured.py             # Bind + invoke structured LLM output
│   │       ├── core_stock_tools.py       # get_stock_data tool
│   │       ├── technical_indicators_tools.py
│   │       ├── fundamental_data_tools.py
│   │       └── news_data_tools.py
│   │
│   ├── dataflows/                   # Data fetching + vendor routing
│   │   ├── interface.py             # Tool interface, vendor dispatch
│   │   ├── y_finance.py             # yfinance (default vendor)
│   │   ├── alpha_vantage*.py        # Alpha Vantage (alt vendor)
│   │   ├── yfinance_news.py         # Yahoo Finance news
│   │   ├── stockstats_utils.py      # Technical indicator calculations
│   │   ├── stocktwits.py            # StockTwits sentiment data
│   │   └── reddit.py                # Reddit post data
│   │
│   └── llm_clients/                 # LLM provider integrations
│       ├── factory.py               # create_llm_client() dispatch
│       ├── base_client.py           # BaseLLMClient abstract class
│       ├── openai_client.py         # OpenAI + xAI/DeepSeek/Qwen/GLM/MiniMax/OpenRouter/Ollama
│       ├── anthropic_client.py      # Anthropic / Claude
│       ├── google_client.py         # Google Gemini
│       ├── azure_client.py          # Azure OpenAI
│       ├── model_catalog.py         # Available models per provider
│       ├── capabilities.py          # Provider capability matrix
│       ├── api_key_env.py           # API key detection from env
│       └── validators.py            # Model/provider validation
│
├── cli/                             # Typer CLI application
│   ├── main.py                      # CLI entry point, interactive UI, streaming display
│   ├── models.py                    # CLI data models
│   ├── config.py                    # CLI configuration
│   ├── utils.py                     # CLI helpers
│   ├── stats_handler.py             # LLM/tool usage callback tracking
│   └── announcements.py            # Feature announcements
│
└── tests/                           # pytest test suite
    ├── conftest.py                  # Fixtures
    └── test_*.py                    # 22+ test files (unit + integration + smoke)
```

---

## Agent Catalog

| Agent | File | LLM | Structured Output | Role |
|---|---|---|---|---|
| Market Analyst | `analysts/market_analyst.py` | quick_think | No | Technical indicators (MACD, RSI, Bollinger, ATR) |
| Sentiment Analyst | `analysts/sentiment_analyst.py` | quick_think | No | Yahoo news + StockTwits + Reddit (pre-fetched, no tool calls) |
| News Analyst | `analysts/news_analyst.py` | quick_think | No | Macro/geopolitical news |
| Fundamentals Analyst | `analysts/fundamentals_analyst.py` | quick_think | No | Revenue, earnings, balance sheet, cash flow |
| Bull Researcher | `researchers/bull_researcher.py` | quick_think | No | Bullish debate arguments |
| Bear Researcher | `researchers/bear_researcher.py` | quick_think | No | Bearish debate arguments |
| Research Manager | `managers/research_manager.py` | deep_think | `ResearchPlan` | Synthesizes debate → 5-tier rating |
| Trader | `trader/trader.py` | quick_think | `TraderProposal` | Research plan → entry/stop/size |
| Aggressive Debator | `risk_mgmt/aggressive_debator.py` | quick_think | No | Risk aggression arguments |
| Conservative Debator | `risk_mgmt/conservative_debator.py` | quick_think | No | Capital preservation arguments |
| Neutral Debator | `risk_mgmt/neutral_debator.py` | quick_think | No | Balanced risk arguments |
| Portfolio Manager | `managers/portfolio_manager.py` | deep_think | `PortfolioDecision` | Final decision + price target |

### Output Schemas (`tradingagents/agents/schemas.py`)

**ResearchPlan**
```python
recommendation: PortfolioRating   # Buy | Overweight | Hold | Underweight | Sell
rationale: str
strategic_actions: list[str]
```

**TraderProposal**
```python
action: TraderAction              # Buy | Hold | Sell
reasoning: str
entry_price: float
stop_loss: float
position_sizing: str
```

**PortfolioDecision**
```python
rating: PortfolioRating           # Buy | Overweight | Hold | Underweight | Sell
executive_summary: str
investment_thesis: str
price_target: float
time_horizon: str
```

---

## Data Sources

| Source | Module | What It Provides |
|---|---|---|
| yfinance | `dataflows/y_finance.py` | OHLCV price history, fundamentals |
| Alpha Vantage | `dataflows/alpha_vantage*.py` | Alternative price + fundamentals + news |
| stockstats | `dataflows/stockstats_utils.py` | Technical indicator calculations |
| Yahoo Finance News | `dataflows/yfinance_news.py` | Ticker-specific news articles |
| StockTwits | `dataflows/stocktwits.py` | Retail sentiment + cashtag messages |
| Reddit | `dataflows/reddit.py` | Posts from r/wallstreetbets, r/stocks, r/investing |

Data vendor is selected via `config["data_provider"]`. The `dataflows/interface.py` module routes tool calls to the active vendor.

**Crypto mode**: When `asset_type = "crypto"`, the system skips fundamentals and switches to crypto-appropriate data paths.

---

## Persistence & Recovery

### Decision Log

Written to `~/.tradingagents/memory/trading_memory.md` after every run. Append-only markdown with entries:

```
[2026-01-15 | NVDA | Buy | pending]
```

The Portfolio Manager reads same-ticker and cross-ticker lessons from this log on each run via `past_context`. After outcomes are known, entries can be reflected on and updated with a result.

### Checkpointing

Opt-in SQLite checkpoint per ticker at `~/.tradingagents/cache/checkpoints/<TICKER>.db`.

```bash
tradingagents analyze --checkpoint            # Enable
tradingagents analyze --clear-checkpoints     # Reset before run
```

Saves state after every node. If a run is interrupted, re-running with `--checkpoint` resumes from the last completed node rather than restarting.

### Run Logs

Full state JSON is saved to `~/.tradingagents/logs/<TICKER>/TradingAgentsStrategy_logs/` after each run, including all analyst reports and debate history.

---

## GCP Deployment

The Terraform module in `terraform/` provisions a complete production environment targeting a single US user. The `api/` container serves both the FastAPI backend and the React web dashboard as a single unit — the same image that runs locally via `docker compose up api`.

### Architecture

```text
GitHub push to main
  │
  ▼
Cloud Build (cloudbuild.yaml)
  ├─ run unit/smoke tests
  ├─ build api/Dockerfile → Artifact Registry
  └─ gcloud run deploy → Cloud Run

User (browser or curl)
  │  authenticated via IAM identity token
  ▼
Cloud Run  (min 0 / max 1 instance, 2 vCPU / 2 GiB, 3600 s timeout)
  │  mounts GCS bucket as /home/appuser/.tradingagents
  │  reads API keys from Secret Manager
  ├─ FastAPI /api/* → TradingAgentsGraph.propagate() + SSE streaming
  └─ StaticFiles / → React web dashboard (ui/dist/)

Persistent data in Cloud Storage
  ├─ memory/trading_memory.md   (decision log)
  ├─ cache/checkpoints/         (SQLite resume files)
  └─ logs/                      (full state JSON per run)
```

**Estimated cost (light use, single user):** ~$2–8/month.  
Cloud Run scales to zero between analyses; cost is ~$0.03 per 10-minute run at 2 vCPU.

### Prerequisites

- GCP project with billing enabled
- `gcloud` CLI authenticated (`gcloud auth login`)
- Terraform ≥ 1.9 (`brew install terraform`)
- Docker (for local image builds)

### First Deployment

#### 1. Configure variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars — set project_id, github_owner, invoker_email
```

#### 2. Provision infrastructure

```bash
terraform init
terraform apply
# note the cloud_run_url and artifact_registry_repo outputs
```

#### 3. Populate secrets (repeat for each LLM provider key you use)

```bash
echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```

Then add the secret name to `active_secrets` in `terraform.tfvars` and re-apply:

```bash
terraform apply
```

#### 4. Build and push the initial image

```bash
REPO=$(terraform output -raw artifact_registry_repo)
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -f api/Dockerfile -t $REPO/app:latest .
docker push $REPO/app:latest
gcloud run deploy tradingagents --image=$REPO/app:latest --region=us-central1
```

After this, every push to `main` triggers Cloud Build automatically.

#### 5. Connect Cloud Build to GitHub

In the GCP Console → Cloud Build → Triggers → click **tradingagents-deploy** → Connect Repository (authorise GitHub and select the repo). Subsequent pushes to `main` deploy automatically.

### Running an Analysis

```bash
URL=$(gcloud run services describe tradingagents --region=us-central1 --format='value(status.url)')

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","date":"2026-01-15","llm_provider":"openai"}' \
  $URL/analyze
```

Or use the pre-built command from Terraform output:

```bash
terraform output -raw analyze_curl | bash
```

### Accessing Persistent Data

```bash
# Download the decision log
gsutil cp gs://$(terraform output -raw data_bucket)/memory/trading_memory.md .

# List all run logs
gsutil ls gs://$(terraform output -raw data_bucket)/logs/
```

### Feature Releases

Push to `main` → Cloud Build runs tests → builds new image → deploys the new revision → Cloud Run shifts traffic to it automatically. Zero downtime, no manual steps.

To roll back: `gcloud run services update-traffic tradingagents --to-revisions=PREV_REVISION=100 --region=us-central1`

---

## Key Extension Points

| What to extend | Where |
| --- | --- |
| Add a new analyst | `tradingagents/agents/analysts/` + register in `tradingagents/graph/setup.py` + add field to `_WATCHED_FIELDS` in `trading_graph.py` |
| Add a new LLM provider | `tradingagents/llm_clients/` (subclass `BaseLLMClient`, add to `factory.py`, `model_catalog.py`, `capabilities.py`) |
| Add a new data source | `tradingagents/dataflows/` (implement tool, register in `interface.py`) |
| Modify debate round limits | `config["max_debate_rounds"]` or `TRADINGAGENTS_MAX_DEBATE_ROUNDS` env var |
| Add structured output fields | `tradingagents/agents/schemas.py` (Pydantic models) |
| Change routing logic | `tradingagents/graph/conditional_logic.py` |
| Modify state fields | `tradingagents/agents/utils/agent_states.py` (TypedDict) |
| Extend the CLI | `cli/main.py` |
| Extend the web API | `api/main.py` (add routes; persist to `~/.tradingagents/`) |
| Extend the web UI | `ui/src/pages/` (add page) + `ui/src/App.tsx` (add route) |
