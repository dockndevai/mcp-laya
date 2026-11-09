# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-11-09

### Changed
- Raised the `setuptools` build-system minimum from `>=83.0.0` to `>=84.1.0` to pick up the fix for
  [GHSA-xmj3-9gf7-h52w](https://osv.dev/vulnerability/GHSA-xmj3-9gf7-h52w) (a Windows-only wheel
  install path that could write a fixed-content `__init__.py` outside the destination directory via
  attacker-controlled `namespace_packages.txt` metadata).
- Raised the `mcp` dependency minimum from `>=2.0.0` to `>=2.2.0` to pick up fixes for four advisories
  affecting `mcp` 2.0.0–2.1.1: unbounded Streamable HTTP session memory growth
  ([GHSA-84m7-p3x7-pcfv](https://osv.dev/vulnerability/GHSA-84m7-p3x7-pcfv)), cross-origin redirect
  following that could leak client credentials
  ([GHSA-5h93-6whr-6q8j](https://osv.dev/vulnerability/GHSA-5h93-6whr-6q8j)), missing token-audience
  validation ([GHSA-w4fh-qvv9-3v23](https://osv.dev/vulnerability/GHSA-w4fh-qvv9-3v23)), and SSRF via
  unresolved `$ref`s in tool output-schema validation
  ([GHSA-rwrf-2pqf-9j8j](https://osv.dev/vulnerability/GHSA-rwrf-2pqf-9j8j)). mcp-laya runs a stdio
  server only (no Streamable HTTP, no outbound client calls to other MCP servers), so none of these
  apply to how it is used here; the bump is routine dependency hygiene so the floor cannot resolve to
  a vulnerable `mcp`. `laya` constraint is unchanged. No source changes.

## [0.1.2] - 2026-10-12

### Changed
- Raised the `setuptools` build-system minimum from `>=61.0` to `>=83.0.0` to pick up the fix for
  PYSEC-2026-3447 (a `MANIFEST.in` Unicode-normalization bypass in `sdist` builds on macOS
  APFS/HFS+), flagged by `pip-audit` against the resolved dev environment. No runtime dependency
  changes; `mcp` and `laya` constraints are unchanged and resolve to current, non-vulnerable
  versions.

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
