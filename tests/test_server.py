"""In-process tests of the real MCP server object (needs `mcp`, not torch or laya)."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

from mcp_laya import __version__, server

EXPECTED_TOOLS = {
    "decide", "classify", "score", "check", "triage", "detect_language", "explain_routing", "list_models",
}


def _tools():
    return asyncio.run(server.mcp.list_tools())


def _audit(capsys) -> list[dict]:
    return [json.loads(ln) for ln in capsys.readouterr().err.splitlines() if ln.startswith("{")]


@pytest.fixture(autouse=True)
def _no_laya(monkeypatch):
    """These tests must never import laya/torch; fail loudly if a code path tries."""
    monkeypatch.setattr(server._engine, "_import_laya", lambda: pytest.fail("laya must not be imported"))


def test_exposes_exactly_the_documented_tools():
    assert {t.name for t in _tools()} == EXPECTED_TOOLS


def test_every_tool_is_annotated_read_only():
    for t in _tools():
        assert t.annotations is not None, t.name
        assert t.annotations.read_only_hint is True, t.name


def test_package_version_matches_pyproject_and_server_json():
    root = Path(__file__).parent.parent
    py = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.M)
    assert py and py.group(1) == __version__
    reg = json.loads((root / "server.json").read_text())
    assert reg["version"] == __version__
    assert [p["version"] for p in reg["packages"]] == [__version__]


def test_list_models_works_without_laya():
    out = asyncio.run(server.mcp.call_tool("list_models", {}))
    assert out is not None


# --- item 6, through the real tool functions: refusals happen before laya/torch is imported ---
def test_triage_unknown_preset_refused_before_laya(capsys):
    with pytest.raises(RuntimeError, match="Unknown preset"):
        server.triage("hello", preset="nope")
    (line,) = _audit(capsys)
    assert line["outcome"] == "rejected" and line["tool"] == "triage"


def test_triage_disallowed_model_refused_before_laya(capsys):
    with pytest.raises(RuntimeError, match="not permitted"):
        server.triage("hello", model="not-a-model")
    (line,) = _audit(capsys)
    assert line["outcome"] == "rejected" and line["tool"] == "triage:triage"


def test_triage_oversized_state_refused_before_laya():
    with pytest.raises(RuntimeError, match="LAYA_MAX_INPUT_CHARS"):
        server.triage("x" * (server._config.max_input_chars + 1))


# --- item 3: validation failures that happen in the tool, before guard(), are audited too ---
def test_classify_without_labels_is_audited(capsys):
    with pytest.raises(RuntimeError, match="labels"):
        server.classify("hello")
    (line,) = _audit(capsys)
    assert line["outcome"] == "rejected" and line["tool"] == "classify"


def test_score_with_one_level_is_audited(capsys):
    with pytest.raises(RuntimeError, match="two ordered"):
        server.score("hello", "how urgent?", ["only"])
    (line,) = _audit(capsys)
    assert line["outcome"] == "rejected" and line["tool"] == "score"


# --- item 2, through the real tool function ---
def test_decide_with_oversized_instructions_refused(capsys):
    big = {"q": {"type": "noul", "instructions": "x" * (server._config.max_input_chars + 1)}}
    with pytest.raises(RuntimeError, match="Questions are"):
        server.decide("hello", big)
    assert _audit(capsys)[0]["outcome"] == "rejected"
