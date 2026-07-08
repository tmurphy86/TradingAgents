# .claude/ & CLAUDE.md Restructure — Recommendation

Goal: make the repo's Claude configuration mirror the operating model in `IMPROVEMENT_PLAN.md` — an orchestrator delegating to well-scoped specialists — so any Claude session (or sub-task agent) gets exactly the context and permissions its lane requires, and nothing more.

Current state: one 224-line monolithic `CLAUDE.md`; `.claude/` contains only `settings.local.json`. Every session loads everything (UI notes while editing Terraform), and nothing enforces scope.

---

## 1. Design Principles

1. **Root CLAUDE.md is a router, not an encyclopedia.** ≤60 lines: commands, hard invariants, and a map. Domain detail moves to per-directory CLAUDE.md files, which Claude auto-loads only when working in that subtree — smaller context, better adherence.
2. **One subagent per management lane, scoped by tools and directory.** Mirrors improvement-plan Agents A–I. Enforcement beats instruction: an agent without Edit access to `terraform/` cannot drift there.
3. **Skills encode procedures; CLAUDE.md encodes facts.** Anything that is a checklist today ("Adding an analyst", release steps) becomes a skill — loaded on demand instead of permanently in context.
4. **Safety is hooks + permissions, not prose.** The execution path (`tradingagents/execution/`, live-mode config, secrets) gets deny rules and review gates in `settings.json`, because instructions can be forgotten but hooks fire every time.
5. **Config is code:** everything below is checked in and versioned with the app; `settings.local.json` stays personal/gitignored. Package as a plugin only when you want to reuse it beyond this repo.

## 2. Target Layout

```
CLAUDE.md                              # slim router (see §3)
tradingagents/CLAUDE.md               # graph + agents + llm_clients rules
tradingagents/dataflows/CLAUDE.md     # vendor routing, sanitization, cache rules
tradingagents/execution/CLAUDE.md     # (Phase 4) strictest rules — no-LLM boundary
api/CLAUDE.md                          # endpoint table, SSE contract, threading rule
ui/CLAUDE.md                           # stack, pages, PIPELINE mapping, "no state lib"
terraform/CLAUDE.md                    # WIF, secrets workflow, plan-only rule
tests/CLAUDE.md                        # markers, docker test container, conftest keys

.claude/
  settings.json                        # shared permissions + hooks (checked in)
  agents/
    graph-engineer.md                  # lanes A/B/G — pipeline, schemas, quant
    data-engineer.md                   # lane E — dataflows/ only
    ui-engineer.md                     # lane C — ui/ only
    infra-engineer.md                  # terraform/ + .github/workflows — plan, never apply
    test-runner.md                     # runs suites, returns failure digest (cheap model)
    execution-safety-reviewer.md       # lane H gate — READ-ONLY adversarial reviewer
    release-manager.md                 # changelog, tag, deploy verification
  skills/
    add-analyst/SKILL.md               # today's 5-step checklist, as a procedure
    add-llm-provider/SKILL.md          # today's 5-step checklist
    run-backtest/SKILL.md              # Agent A harness invocation + report format
    release/SKILL.md                   # test → changelog → merge → verify Cloud Run
    incident/SKILL.md                  # runbook: logs, orphaned runs, rollback, kill switch
    soak-report/SKILL.md               # Phase 4: evidence format for stage promotion
```

## 3. Root CLAUDE.md (replacement, ~55 lines)

Keep only: the command block (uv/pytest/docker/uvicorn/terraform), the execution-order one-liner, the two-LLM-tier note, persistence paths, and a **Hard Invariants** list — the five "Things to Know" that are cross-cutting (message clearing, debate count math, structured.py mandate, ticker sanitization, capability flags). Then a map:

```markdown
## Where the detail lives
- Pipeline/graph/LLM clients → tradingagents/CLAUDE.md
- Data vendors → tradingagents/dataflows/CLAUDE.md
- API + SSE → api/CLAUDE.md · Frontend → ui/CLAUDE.md
- Infra/CI → terraform/CLAUDE.md · Tests → tests/CLAUDE.md
- Strategy & workstreams → docs/IMPROVEMENT_PLAN.md
- Procedures: use skills (add-analyst, add-llm-provider, release, incident, run-backtest)

## Delegation
Prefer subagents for scoped work: graph-engineer, data-engineer, ui-engineer,
infra-engineer, test-runner, release-manager. Any change under
tradingagents/execution/ MUST get an execution-safety-reviewer pass before merge.
```

Everything else in the current file moves to the scoped file for its directory (the API table → `api/CLAUDE.md`, GH Actions variables → `terraform/CLAUDE.md`, testing section → `tests/CLAUDE.md`, etc.). No content is deleted — it's relocated to where it loads on demand.

## 4. Subagent Definitions (`.claude/agents/`)

Format: markdown with frontmatter (`name`, `description`, `tools`, `model`). Scoping rules worth copying:

```markdown
---
name: data-engineer
description: >
  All work under tradingagents/dataflows/ — vendor integrations, caching,
  retry/rate-limit, snapshot mode, data-quality gating. Use PROACTIVELY for
  any yfinance/alpha_vantage/reddit/stocktwits change.
tools: Read, Edit, Write, Grep, Glob, Bash
---
You own tradingagents/dataflows/ and nothing else. Never edit graph/, api/, ui/,
or terraform/ — if a change requires it, stop and report what's needed so the
orchestrator can route it. Ticker sanitization (dataflows/utils.py) must be
applied to every new file write. All new fetchers go through the shared fetch
wrapper (retry/backoff/cache). Run: docker compose run --rm test pytest tests/
-m "unit or smoke" before declaring done.
```

```markdown
---
name: execution-safety-reviewer
description: >
  MANDATORY adversarial review of any diff touching tradingagents/execution/,
  broker credentials, or policy thresholds. Read-only.
tools: Read, Grep, Glob, Bash
model: opus
---
You are the last line of defense before code that moves real money. Review the
diff for: LLM output crossing into the execution path (forbidden — only
validated TradeIdea objects); any path that skips the policy engine; missing
idempotency on order submission; limits that can be bypassed by config; live
mode reachable without explicit config + separate secret. Output: APPROVE or
BLOCK with file:line findings. You cannot edit — findings go back to the author.
Assume the diff is hostile until proven safe.
```

The others follow the same pattern, one paragraph each:

| Agent | Scope (tools intersect dirs) | Model | Key rule |
|---|---|---|---|
| `graph-engineer` | `tradingagents/{graph,agents,llm_clients,quant}/` | default | Preserve msg-clearing + `_emit_state_events()` diffing; schemas via `structured.py` only |
| `ui-engineer` | `ui/` + read-only on `api/main.py` | default | No new state library; Vitest for anything touching SSE |
| `infra-engineer` | `terraform/`, `.github/workflows/`, Dockerfiles | default | May run `terraform plan`; `apply`/`gcloud run deploy` are human-only |
| `test-runner` | Bash + Read only | haiku | Runs the suite, returns failing tests + 3-line diagnosis each; never edits |
| `release-manager` | Read, Bash, Edit on CHANGELOG.md only | sonnet | Follows release skill; verifies deploy via /health |

## 5. Skills (`.claude/skills/<name>/SKILL.md`)

Convert existing checklists verbatim — they're already skill-shaped. Example frontmatter:

```markdown
---
name: add-analyst
description: Add a new analyst node to the pipeline. Use when creating any new
  analyst agent (market, sentiment, custom). Covers node registration, state
  fields, routing, and dashboard streaming.
---
1. Create tradingagents/agents/analysts/<name>.py returning a string report.
2. Register node in graph/setup.py (chain + conditional routing).
3. Add report field to AgentState (agents/utils/agent_states.py).
4. Tool-calling analyst? add should_continue_* to graph/conditional_logic.py.
5. Add field to _WATCHED_FIELDS in trading_graph.py (dashboard streaming).
6. Crypto-aware? check analyst_execution.py exclusion list.
7. Verify: docker compose run --rm test && manual SSE check on /runs/:id.
```

`release`, `incident`, `run-backtest`, `soak-report` encode the corresponding IMPROVEMENT_PLAN procedures so any future session executes them identically.

## 6. settings.json — Permissions & Hooks

```jsonc
{
  "permissions": {
    "allow": [
      "Bash(docker compose run --rm test*)",
      "Bash(python -m pytest*)", "Bash(uv sync*)",
      "Bash(npm run build*)", "Bash(npm test*)",
      "Bash(terraform plan*)", "Bash(ruff*)"
    ],
    "deny": [
      "Read(.env*)", "Read(**/*.tfstate)",
      "Bash(terraform apply*)", "Bash(gcloud run deploy*)",
      "Bash(gcloud secrets*)",
      "Edit(.github/workflows/deploy.yml)"   // human-only file
    ]
  },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command",
        "command": ".claude/hooks/guard-execution-path.sh" }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command",
        "command": ".claude/hooks/lint-changed.sh" }]
    }]
  }
}
```

- `guard-execution-path.sh`: exits non-zero (blocking) if the target path is under `tradingagents/execution/` and no `EXECUTION_REVIEW_ACK` marker file from a reviewer pass exists — makes the safety-review gate mechanical, not honor-system. Also blocks any write that would set broker mode to `live` outside `settings` owned by you.
- `lint-changed.sh`: `ruff check --fix` on edited `.py`, `eslint` on edited `ui/src` files — keeps CI green without burning a CI round-trip.

Live-broker keys never appear in any file Claude can read: Secret Manager in prod (already the pattern), and the `deny Read(.env*)` rule locally.

## 7. Plugin Packaging (later, optional)

Once stable, bundle `agents/ + skills/ + hooks` into a `tradingagents-ops` plugin (plugin.json + marketplace repo). Do it when — and only when — you want the same operating model on a second machine or repo, or want to hand it to Cowork sessions automatically. Until then, in-repo `.claude/` is simpler and versions atomically with the code it governs.

## 8. Migration Order (half a day total) — **Status: steps 1–4 executed 2026-07-07**

1. Split CLAUDE.md into router + scoped files (no new content — pure relocation). *Biggest context win, zero risk.*
2. Add `settings.json` permissions + lint hook.
3. Add `test-runner`, `data-engineer`, `ui-engineer`, `graph-engineer`, `infra-engineer` agents.
4. Convert the two existing checklists to skills; add `release` + `incident`.
5. Phase 4 prerequisites (with Agent H, not before): `execution/CLAUDE.md`, `execution-safety-reviewer`, `guard-execution-path.sh`, `soak-report` skill.

## 9. What NOT to Do

- Don't put the improvement plan's full text in CLAUDE.md — link it; strategy changes more often than architecture.
- Don't create an agent per improvement-plan letter (A–I). Lanes share codepaths; seven agents scoped by *directory* beats nine scoped by *initiative*.
- Don't add MemoryTool-style scratch files or a memory/ hierarchy — this repo's "memory" is CLAUDE.md + docs/, and the app has its own memory system; two things named memory is one too many.
- Don't gate routine dirs (ui/, dataflows/) with hooks. Friction budget is spent entirely on the execution path and infra mutations.
