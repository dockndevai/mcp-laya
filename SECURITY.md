# Security

`mcp-laya` runs a local decision model (Laya) and exposes it to an AI agent as typed-decision tools.
It is **read-only**: it reads a state and returns a decision, and never mutates anything, calls out to
other systems, or executes code. That makes it the lowest-risk server in the suite — the guardrails
are about **privacy and resource control**, not write-gating.

## Principles

- **Everything runs locally.** Inference happens on your machine/GPU. No request data — the text,
  email, ticket or JSON you evaluate — is ever sent anywhere.
- **Offline by default.** The one time anything touches the network is the initial download of the
  Laya checkpoints from Hugging Face. That is **disabled** unless `LAYA_ALLOW_DOWNLOAD=true`. Pre-fetch
  the models once, then run fully offline. In offline mode a missing checkpoint fails fast with a
  clear message rather than reaching out silently.
- **Model allowlist.** `LAYA_MODELS` pins which checkpoints may load; an explicit `model=` outside the
  allowlist is refused.
- **Request bounds.** `LAYA_MAX_INPUT_CHARS` and `LAYA_MAX_QUESTIONS` cap each call, so a runaway
  prompt can't exhaust memory.
- **Confidence honesty.** Every answer carries a calibrated `confidence`. `LAYA_MIN_CONFIDENCE` flags
  answers below a threshold with `low_confidence: true` — it never silently drops or "upgrades" them.
  Treat a low-confidence decision as a signal to ask the bigger model, not as ground truth.
- **Log privacy.** With `LAYA_REDACT_STATE=true` (default), the JSON audit line records the tool,
  chosen model, input size and question ids — but **not** the input text.

## Limitations

- Laya makes **judgments**, not facts. Use `confidence` for control flow; don't treat a decision as
  verified truth, especially near 0.5 or when `low_confidence` is set.
- Some checkpoints may report uncalibrated confidence for certain question shapes (Laya warns on
  load). Weight those accordingly.
- This server does not fine-tune, train, or modify the model; it only runs inference with the
  published checkpoints.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository rather than a public issue. Issues in
the underlying model belong upstream at the [laya](https://github.com/NandhaKishorM/laya) project.
