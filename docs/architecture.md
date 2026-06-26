# Architecture

## Layered design

Ledger has four layers. Each is independently testable and replaceable.

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI / Agent Interface                     │
│  ledger ask "..."   ledger ingest ...   ledger eval ...      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                       Agent Layer                            │
│  Claude + tools: query_ledger, search_txns, compute_returns  │
│  Planner → executor → validator (confidence + grounding)     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                       Store Layer                            │
│   SQLite (canonical ledger)  +  DuckDB (analytics views)     │
│   Schema: accounts, transactions, categorizations, lots      │
└─────────────────────▲───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                      Ingest Layer                            │
│  ingest/chase.py   ingest/citi.py   ingest/fidelity.py ...   │
│  Each parser: bytes → list[RawTransaction]                   │
└──────────────────────────────────────────────────────────────┘
```

## Why this shape

**Ingest is deterministic.** No LLMs in the parsing path. Statement layouts
are stable enough that rule-based parsers are more reliable and debuggable
than asking an LLM to extract structured data. We pay the cost of writing
one parser per institution because the alternative — silent extraction errors
on financial data — isn't acceptable.

**Store is canonical.** All downstream code (agent, evals, future analytics)
reads from one normalized schema. If a statement format changes, only the
parser changes — everything else is insulated.

**Agent is stateless per query.** Every NL question kicks off a fresh agent
loop. The agent has tools, not memory. Long-running memory comes in Phase 4
and lives in a separate `memory/` module, not embedded in the agent.

**Evals are first-class.** Not a side project. Every agent capability has
a labeled eval set. Regressions block merges.

## The agent loop

```
user question
     │
     ▼
[ planner ]  ─→ list of tool calls + reasoning
     │
     ▼
[ executor ] ─→ runs tools, collects results
     │
     ▼
[ validator ] ─→ checks grounding, computes confidence
     │
     ▼
final answer + confidence + audit trail
```

Each agent step is logged with: prompt, tools called, tool inputs/outputs,
final answer, latency, cost. The log is replayable — given the log, we can
reconstruct the exact agent execution. This matters for debugging *and* for
the eval framework.

## Tools

The agent has a small set of typed tools. Adding tools is intentional, not
incidental — each new tool needs an eval contribution.

| Tool | Purpose | Notes |
|------|---------|-------|
| `query_ledger(sql)` | Run read-only SQL against ledger | LLM-generated SQL is validated against schema before execution |
| `search_transactions(query, since, until)` | Semantic search over transaction descriptions | Backed by sqlite-vss or pgvector |
| `compute_returns(account, since, until)` | P&L reconstruction for brokerage account | Pure Python, no LLM |
| `get_category_taxonomy()` | Returns the canonical category list | So the LLM doesn't invent categories |
| `get_account_summary(account_id)` | Account-level summary stats | Read-only |

## Why Claude Code as the dev environment

You'll do most of your development *inside* Claude Code, with the project's
`CLAUDE.md` giving Claude context. This isn't a vanity move — it's the closest
analogue to the FDE workflow at Anthropic and the Applied AI workflow at
Google Cloud. Building a serious project with Claude Code teaches you the
patterns hiring managers ask about.

## What's deliberately not here yet

- No web UI (CLI is fine until features are real)
- No multi-user (this is a single-user personal tool)
- No real-time data (statements are batch; live data is Phase 3)
- No fine-tuning or training (we're application-layer, not model-layer)
- No notifications/scheduling (Phase 4)
