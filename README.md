# Ledger

A personal finance agent that ingests bank, credit card, and brokerage statements
and answers natural-language questions about your money.

Built as a learning project to develop production-grade agentic AI skills:
multi-step reasoning, tool use, structured output, eval rigor, and MCP integration.

## What it does (today)

- Parses PDF and CSV statements from major banks/brokerages into a unified ledger
- Categorizes transactions with confidence scores (low-confidence ones get flagged)
- Answers questions like "how much did I spend on restaurants in Q1?" via a Claude-powered agent that translates NL into structured SQL against your local ledger
- Reconstructs trade P&L from brokerage statements (lots, holding periods, realized gains)

## What it will do (roadmap)

See [docs/roadmap.md](docs/roadmap.md) for the phased plan.

- Phase 1 (current): statement parsing + agent over local SQLite ledger
- Phase 2: Plaid sandbox integration via MCP
- Phase 3: live accounts via Plaid (production) / Teller for Chase
- Phase 4: long-running agent — proactive nudges, anomaly detection, monthly digests

## Setup

### Prerequisites
- Python 3.11+
- `uv` (recommended) or `pip`
- Anthropic API key
- Claude Code installed (optional but recommended — see [docs/architecture.md](docs/architecture.md))

### Install
```bash
git clone https://github.com/<your-username>/ledger.git
cd ledger
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY
```

### Initialize the ledger DB
```bash
ledger init
```

### Ingest a statement
```bash
ledger ingest data/samples/chase_2024_03.pdf
```

### Ask a question
```bash
ledger ask "what did I spend on restaurants in March?"
```

## Architecture

See [docs/architecture.md](docs/architecture.md). High level:

```
statements (PDF/CSV)
      │
      ▼
  ingest layer          ← deterministic parsers per institution
      │
      ▼
   ledger DB            ← canonical normalized schema (SQLite + DuckDB for analytics)
      │
      ▼
   agent layer          ← Claude with tools: query_ledger, compute_returns,
                          search_transactions, get_category_taxonomy
      │
      ▼
   eval harness         ← labeled question set, per-tool unit tests, grounding checks
```

## Development with Claude Code

This repo is set up to be developed *with* Claude Code as your pair programmer.
Key files:

- `CLAUDE.md` — project context Claude Code reads on every session
- `.claude/settings.json` — local MCP server config (gitignored secrets)
- `docs/` — architecture and data model docs Claude Code references

## License

MIT
