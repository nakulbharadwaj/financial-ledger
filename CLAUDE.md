# Ledger — Project Context for Claude Code

You are pair-programming on **Ledger**, a personal finance agent. This file
gives you context that applies across all sessions. Re-read at the start of
each work session.

## Project goals

Ledger is both a personal tool and a portfolio project. Code quality matters
as much as functionality. Specifically:

1. **Production-grade patterns from day one.** No notebook-style code in `src/`.
   Type hints everywhere. Pydantic for data validation. Tests for parsers.
2. **Eval rigor.** Every agent capability should have an eval. We measure
   accuracy on a labeled set before shipping a change.
3. **Auditability.** This is financial data. Every agent decision should be
   loggable and replayable. No silent state mutations.
4. **Modularity.** Ingest, store, agent, and evals should each be independently
   testable and swappable.

## Architecture (short version)

- `src/ledger/ingest/`: statement parsers (one module per institution).
  Each parser returns a `list[RawTransaction]` and must be pure (no DB writes).
- `src/ledger/store/`: SQLAlchemy models + DuckDB analytics views.
  Schema in `store/models.py` is canonical — change with care.
- `src/ledger/agent/`: Claude-powered agent.
  Tools defined in `agent/tools.py`. Each tool is a typed Python function;
  schemas are auto-generated from type hints.
- `src/ledger/evals/`: eval harness.
  `evals/datasets/` holds labeled question sets. `evals/runners/` executes them.

## Coding conventions

- Python 3.11+, type hints required on all public functions.
- Pydantic v2 for all data models that cross module boundaries.
- `ruff` for linting and formatting (not black, not isort).
- `pytest` for tests. Aim for >80% coverage on `ingest/` and `store/`.
- Use `logging` with structured fields, not print. Logger name = module name.
- No `requests`. Use `httpx`. No `pandas` unless analyzing — use `polars` or raw SQL.

## When writing parsers

PDF bank statement parsing is the hardest part of this project. Conventions:

- Each institution gets its own module (`ingest/chase.py`, `ingest/citi.py`).
- Parsers should be tested against real (anonymized) statements in `tests/fixtures/`.
- Prefer `pdfplumber` for layout-aware extraction over `PyPDF2`.
- For unparseable rows, raise `ParseError` with the row text and page number
  — never silently drop a transaction.
- Output `RawTransaction` only. Categorization happens later, in the agent layer.

## When working on the agent

- The agent uses Anthropic's Claude via the `anthropic` Python SDK.
- Tools are typed Python functions; we auto-generate the JSON schema.
- The agent should never write to the ledger DB directly. All mutations go
  through explicit tool calls that get logged.
- For any query that touches money: include a confidence score in the response
  and surface the SQL/computation that produced it.

## When working on evals

- Eval datasets live in `evals/datasets/` as JSONL.
- Each eval example: `{"question": ..., "expected_answer": ..., "expected_tools": [...], "rubric": ...}`.
- Run evals via `ledger eval <dataset_name>`. Outputs a markdown report.
- Don't merge changes that drop eval scores without explicit acknowledgment.

## Things NOT to do

- Don't add credential-scraping code for Chase/Citi/etc. We use Plaid or Teller.
- Don't commit anything from `data/` except `data/samples/` (anonymized).
- Don't add a "let's just YOLO an LLM categorization" path without an eval.
- Don't add dependencies without justifying in the PR description.

## Useful context files

- `docs/architecture.md` — full system architecture
- `docs/roadmap.md` — phased plan
- `docs/data-model.md` — canonical ledger schema
