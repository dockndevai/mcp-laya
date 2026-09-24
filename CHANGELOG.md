# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-09-24

### Fixed
- Added the `mcp-name` marker to the README so the MCP Registry can verify PyPI package ownership
  (the registry validates ownership of a PyPI package via a line in its published README). No code
  changes from 0.1.0.

## [0.1.0] - 2026-09-24

### Added
- Initial release: a safe-by-default MCP server for the Laya System-1 decision engine — the suite's
  first Python server. 8 tools: `decide`, `classify`, `score`, `check`, `triage`, `detect_language`,
  `explain_routing`, `list_models`.
- Typed decisions (choice / score / noul) over any state in one local forward pass, 100+ languages,
  no text generation, with a calibrated confidence on every answer; laya's Router auto-selects the
  checkpoint per request.
- Safe-by-default model for read-only inference: **offline by default** (the one-time checkpoint
  download is gated by `LAYA_ALLOW_DOWNLOAD`), a model allowlist, input/question caps, a confidence
  threshold that flags (never silently trusts) low-confidence answers, and a JSON audit log that keeps
  the input text out by default (`LAYA_REDACT_STATE`).
- Built on the Apache-2.0 [laya](https://github.com/NandhaKishorM/laya) library by Convai Innovations
  (a dependency, not vendored). See NOTICE.
