# mcp-laya

[![PyPI](https://img.shields.io/pypi/v/mcp-laya)](https://pypi.org/project/mcp-laya/)
[![CI](https://github.com/dockndevai/mcp-laya/actions/workflows/ci.yml/badge.svg)](https://github.com/dockndevai/mcp-laya/actions/workflows/ci.yml)
[![licence](https://img.shields.io/badge/licence-MIT-blue)](LICENSE)

A **safe-by-default** [Model Context Protocol](https://modelcontextprotocol.io) server for [**Laya**](https://github.com/NandhaKishorM/laya) — a fast, non-autoregressive **System-1 decision engine**. It gives an agent a *thinking* primitive: typed decisions — **classify, score, yes/no** — over any state (text, an email, a ticket, a JSON object), in a **single local forward pass (~33 ms)**, across **100+ languages**, with **no text generation — nothing to parse and nothing to hallucinate**, and a **calibrated confidence** on every answer.

Instead of burning a slow, costly LLM round-trip on "which team should handle this? is it urgent? is this a refund request?", the agent calls a typed tool that answers **locally, in milliseconds, offline**. It's the safest server in the suite — laya only *reads* a state and returns a decision; it changes nothing.

Part of the [dockndevai MCP server suite](https://dockndevai.github.io/) — one governance model across all of them. (This is the first Python server in the suite; the rest are Node/TS.)

## What it gives an agent

| Tool | For |
|---|---|
| `decide` | answer several typed questions (choice/score/noul) in one pass — the full engine |
| `classify` | assign the single best category (one `choice`) |
| `score` | rate on an ordinal scale, e.g. urgency (one `score`) |
| `check` | a yes/no/unknown gate for control flow (one `noul`) |
| `triage` | a ready-made decision set via a laya preset (triage / email / moderation / guard) |
| `detect_language` | script + language of a text (sub-ms, no model) |
| `explain_routing` | which checkpoint would answer, without running inference |
| `list_models` | the checkpoints available, default, device, offline status |

Three checkpoints, auto-routed per request: **english** (ModernBERT-large), **multilingual** (mmBERT, 100+ languages), **typed-decisions**.

## Install

```bash
pipx install mcp-laya      # or: pip install mcp-laya
```

Python 3.10+. laya pulls in `torch`; the model checkpoints download **once** from Hugging Face (see below), after which it runs fully offline.

## First run: fetch the model once

Downloads are **off by default** (nothing leaves your machine at runtime). Pre-fetch the checkpoints one time with network access:

```bash
LAYA_ALLOW_DOWNLOAD=true python -c "import laya; laya.Router(preload=True)"
```

Then run the server offline.

## Configure

```json
{
  "mcpServers": {
    "laya": {
      "command": "mcp-laya",
      "env": { "LAYA_DEFAULT_MODEL": "auto" }
    }
  }
}
```

See [docs/CLIENTS.md](docs/CLIENTS.md) for Claude Code / Cursor / Codex / VS Code / Windsurf, and [.env.example](.env.example) for every variable.

## Example

Ask your agent to *"use laya to classify this ticket's department and whether it's a churn risk"*:

```jsonc
// classify(state, criteria={billing, technical, sales, other})
{ "choice": "billing", "confidence": 0.95, "probabilities": { "billing": 0.95, ... } }
// check(state, "Does the user threaten to cancel?")
{ "answer": "yes", "probability_yes": 0.91, "confidence": 0.91 }
```

## Safe by default

laya is read-only inference, so the guardrails (in [`src/mcp_laya/security.py`](src/mcp_laya/security.py)) are about privacy and resource control, not write-gating:

- **Offline by default** — the model runs locally; nothing is sent anywhere. The one exception, the first-time checkpoint download, is disabled unless `LAYA_ALLOW_DOWNLOAD=true`.
- **Model allowlist** — `LAYA_MODELS` pins which checkpoints may load.
- **Input caps** — `LAYA_MAX_INPUT_CHARS` / `LAYA_MAX_QUESTIONS` bound each request.
- **Confidence honesty** — `LAYA_MIN_CONFIDENCE` flags (never silently trusts) low-confidence answers; every answer already carries a calibrated `confidence`.
- **Log privacy** — `LAYA_REDACT_STATE` keeps the input text out of the JSON audit log by default.

There's a bundled skill, [`laya-decisions`](.claude/skills/laya-decisions/SKILL.md), teaching an agent when to offload a decision to laya and how to phrase typed questions. See also [SECURITY.md](SECURITY.md).

## Developing

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests && mypy src && pytest      # the policy tests need no model
python -m mcp_laya                              # run the server (stdio)
```

## Credits

Built on **[laya](https://github.com/NandhaKishorM/laya)** by Convai Innovations (Apache-2.0). This server wraps that library; all model work is theirs. See [NOTICE](NOTICE).

## Licence

MIT
