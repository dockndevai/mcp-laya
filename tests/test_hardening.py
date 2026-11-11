"""Regression tests for the 0.1.4 hardening fixes — pure policy/engine logic, no torch, no model."""
from __future__ import annotations

import json
import sys
import types
from dataclasses import replace

import pytest

from mcp_laya.config import Config
from mcp_laya.engine import EngineError, LayaEngine
from mcp_laya.security import PolicyError, SecurityPolicy


def audit_lines(capsys) -> list[dict]:
    err = capsys.readouterr().err
    return [json.loads(line) for line in err.splitlines() if line.startswith("{")]


def policy(**overrides) -> SecurityPolicy:
    return SecurityPolicy(replace(Config(), **overrides))


# --- item 1: offline switch is forced, not defaulted ------------------------------------------
@pytest.mark.parametrize("inherited", ["0", "false", ""])
def test_offline_switches_forced_when_downloads_disallowed(monkeypatch, inherited):
    monkeypatch.setenv("HF_HUB_OFFLINE", inherited)
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", inherited)
    monkeypatch.setitem(sys.modules, "laya", types.ModuleType("laya"))  # no torch needed
    LayaEngine(Config(allow_download=False))._import_laya()
    import os

    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_offline_switches_untouched_when_downloads_allowed(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    monkeypatch.setitem(sys.modules, "laya", types.ModuleType("laya"))
    LayaEngine(Config(allow_download=True))._import_laya()
    import os

    assert os.environ["HF_HUB_OFFLINE"] == "0"
    assert "TRANSFORMERS_OFFLINE" not in os.environ


# --- item 2: the size cap covers the serialized questions -------------------------------------
def test_oversized_question_instructions_rejected():
    p = policy(audit_log=False, max_input_chars=1000)
    big = {"q": {"type": "noul", "instructions": "x" * 5000}}
    with pytest.raises(PolicyError, match="Questions are .* chars serialized"):
        p.guard("check", "hello", big, None)


def test_oversized_criteria_rejected():
    p = policy(audit_log=False, max_input_chars=1000)
    criteria = {f"l{i}": "d" * 100 for i in range(50)}
    big = {"q": {"type": "choice", "instructions": "pick", "criteria": criteria}}
    with pytest.raises(PolicyError, match="LAYA_MAX_INPUT_CHARS"):
        p.guard("decide", "hello", big, None)


def test_normal_sized_questions_still_pass():
    p = policy(audit_log=False, max_input_chars=1000)
    ok = {"q": {"type": "noul", "instructions": "Is this a refund request?"}}
    assert p.guard("check", "hello", ok, None).state_chars == 5


# --- item 3: refused requests are audited too -------------------------------------------------
def test_rejected_model_is_audited(capsys):
    p = policy(models=("english",))
    with pytest.raises(PolicyError, match="not permitted"):
        p.guard("check", "hello", {"q": {}}, "multilingual")
    (line,) = audit_lines(capsys)
    assert line["outcome"] == "rejected" and line["tool"] == "check"
    assert line["model"] == "multilingual" and "not permitted" in line["reason"]


def test_rejected_empty_state_and_oversize_are_audited(capsys):
    p = policy(max_input_chars=10)
    for state in ("", "x" * 11):
        with pytest.raises(PolicyError):
            p.guard("check", state, {"q": {}}, None)
    lines = audit_lines(capsys)
    assert [ln["outcome"] for ln in lines] == ["rejected", "rejected"]
    assert lines[1]["state_chars"] == 11


def test_allowed_call_is_audited_as_allowed(capsys):
    policy().guard("check", "hello", {"q": {}}, None)
    (line,) = audit_lines(capsys)
    assert line["outcome"] == "allowed" and "reason" not in line


def test_rejected_audit_line_is_bounded(capsys):
    p = policy(max_questions=2)
    many = {("k" * 500) + str(i): {} for i in range(100)}
    with pytest.raises(PolicyError):
        p.guard("decide", "hello", many, None)
    (line,) = audit_lines(capsys)
    assert len(line["questions"]) <= 2 and all(len(q) <= 64 for q in line["questions"])


def test_reject_helper_raises_and_audits_when_audit_disabled(capsys):
    with pytest.raises(PolicyError, match="nope"):
        policy(audit_log=False).reject("classify", "hello", "nope")
    assert audit_lines(capsys) == []


# --- item 6: validate before importing laya/torch ---------------------------------------------
def test_unknown_preset_rejected_without_importing_laya(monkeypatch):
    monkeypatch.delitem(sys.modules, "laya", raising=False)
    eng = LayaEngine(Config())
    called = []
    monkeypatch.setattr(eng, "_import_laya", lambda: called.append(1))
    with pytest.raises(EngineError, match="Unknown preset"):
        eng.preset_questions("nope")
    with pytest.raises(EngineError, match="Unknown preset"):
        eng.validate_preset("x" * 500)
    assert called == []


def test_known_preset_validates_without_importing_laya(monkeypatch):
    eng = LayaEngine(Config())
    monkeypatch.setattr(eng, "_import_laya", lambda: pytest.fail("laya must not be imported"))
    eng.validate_preset("triage")
