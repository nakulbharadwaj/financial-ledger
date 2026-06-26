# Roadmap

Phased plan. Each phase ends with a shippable, demoable, eval-tested artifact.

## Phase 1 — Statements + Q&A agent (weekends 1–4)

**Goal:** Ingest 3 institutions' statements, build a ledger, answer 10 canned
questions correctly.

- [ ] Ledger DB schema (accounts, transactions, categorizations, lots)
- [ ] Chase credit card PDF parser
- [ ] One other institution's parser (Citi or Amex)
- [ ] CSV parser (generic fallback)
- [ ] `ledger ingest <file>` CLI
- [ ] `ledger ask <question>` CLI
- [ ] Agent with 3 tools: `query_ledger`, `search_transactions`, `get_category_taxonomy`
- [ ] Categorization with confidence + low-confidence flagging
- [ ] Eval set v1 (20 hand-labeled Q&A pairs)
- [ ] `ledger eval` runs against the eval set and emits a markdown report

**Definition of done:** I can drop my last 3 months of statements into
`data/raw/`, run `ledger ingest data/raw/*.pdf`, and ask "how much did I spend
on restaurants in the last 3 months?" and get the right answer. Eval score ≥ 80%.

## Phase 2 — Trade journal (weekends 5–6)

**Goal:** Brokerage statements → reconstructed trades with P&L.

- [ ] Brokerage statement parser (Fidelity or Schwab — whichever you actually use)
- [ ] Lot tracking in schema (FIFO matching)
- [ ] `compute_returns` tool
- [ ] Trade journal generation: per closed position, a structured journal entry
  (entry date, exit date, holding period, basis, proceeds, P&L, P&L %)
- [ ] Eval extension: 10 brokerage-specific Q&A pairs

**Definition of done:** Drop a quarterly brokerage statement in, get a trade
journal markdown out that matches my broker's reported realized gains within
$0.01.

## Phase 3 — Plaid integration via MCP (weekends 7–8)

**Goal:** Replace manual statement uploads with Plaid-fetched transactions.

- [ ] Plaid sandbox account linked
- [ ] `src/ledger/mcp/plaid_server.py` — MCP server exposing Plaid tools
- [ ] Plaid → ledger sync (idempotent — re-running should be a no-op)
- [ ] Move from sandbox to development tier
- [ ] Optional: Teller integration for Chase (since Chase's Plaid OAuth is finicky)

**Definition of done:** `ledger sync` pulls the last 30 days of transactions
from at least one real account and reconciles correctly against a manual
statement.

## Phase 4 — Long-running agent (weekends 9–12)

**Goal:** Proactive agent — runs on a schedule, surfaces things you'd care about.

- [ ] Anomaly detector (transaction is N stdev above category mean)
- [ ] Recurring subscription tracker
- [ ] Monthly digest generator
- [ ] Memory module (episodic + semantic split) — Claude remembers what
      you've flagged as "not anomalies"
- [ ] Notification surface (email digest, or Slack DM to yourself)
- [ ] Cost tracking and observability dashboard

**Definition of done:** Every Monday morning I get a digest that includes
one or two specific things I would have wanted to know.

## Phase 5 — Eval framework extraction (later)

When the eval harness in `src/ledger/evals/` matures, extract it as a
standalone open-source package. This is the public artifact that goes on
your resume. See `docs/eval-extraction-plan.md` (to be written).
