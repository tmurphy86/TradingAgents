# TradingAgents — Human Test Issues

> **Tim: this is your bug inbox.** Add an entry any time something breaks or behaves wrong — a title and one or two sentences is enough; paste stack traces raw inside the code fence. No formatting rules, no triage duty. Commit or just save; the eng lead does the rest.
> Production incidents with postmortems live in [INCIDENTS.md](INCIDENTS.md) (via the `incident` skill); this file is for everything you notice while using the app.
>
> **Eng lead: this file is step 1 of every session** (before BACKLOG.md). Triage every `status: new` entry into a BUG ticket, set `status: triaged (BUG-###)`, and fix ALL open bugs before dispatching any feature ticket. When fixed+verified, set `status: fixed (commit)`. Never delete entries; the history is the regression map. Every bug fix MUST include a regression test that fails on the pre-fix code.

## Template (copy below the line)

```
### [short title]
- **status:** new
- **date:** YYYY-MM-DD
- **where:** page/feature
- **what happened:**
- **expected:**
- **error output (if any):**
```

---
