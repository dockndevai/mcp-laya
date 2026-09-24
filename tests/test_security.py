"""Unit tests for the pure policy engine and config parsing — no torch, no model download."""
from __future__ import annotations

import os
from dataclasses import replace

import pytest

from mcp_laya.config import Config, load_config
from mcp_laya.security import PolicyError, SecurityPolicy

BASE = Config(audit_log=False)


def policy(**overrides) -> SecurityPolicy:
    return SecurityPolicy(replace(BASE, **overrides))


# --- model allowlist -------------------------------------------------------
def test_auto_returns_none_for_router():
    assert policy().resolve_model(None) is None
    assert policy().resolve_model("auto") is None


def test_explicit_allowed_model_passes():
    assert policy().resolve_model("multilingual") == "multilingual"


def test_model_outside_allowlist_is_rejected():
    p = policy(models=("english",))
    with pytest.raises(PolicyError, match="not permitted"):
        p.resolve_model("multilingual")


def test_default_model_used_when_none_requested():
    assert policy(default_model="english").resolve_model(None) == "english"


# --- request bounds --------------------------------------------------------
def test_empty_state_rejected():
    with pytest.raises(PolicyError, match="Empty state"):
        policy().guard("decide", "", {"q": {}}, None)


def test_oversized_state_rejected():
    p = policy(max_input_chars=10)
    with pytest.raises(PolicyError, match="over the LAYA_MAX_INPUT_CHARS"):
        p.guard("decide", "x" * 11, {"q": {}}, None)


def test_dict_state_length_counted():
    p = policy(max_input_chars=5)
    with pytest.raises(PolicyError):
        p.guard("decide", {"body": "hello world"}, {"q": {}}, None)


def test_too_many_questions_rejected():
    p = policy(max_questions=2)
    with pytest.raises(PolicyError, match="over the LAYA_MAX_QUESTIONS"):
        p.guard("decide", "hi", {"a": {}, "b": {}, "c": {}}, None)


def test_no_questions_rejected():
    with pytest.raises(PolicyError, match="No questions"):
        policy().guard("decide", "hi", {}, None)


def test_guard_allows_questionless_tools():
    # detect_language passes questions=None
    g = policy().guard("detect_language", "bonjour", None, None)
    assert g.state_chars == 7


def test_guard_returns_resolved_model():
    assert policy().guard("decide", "hi", {"q": {}}, "english").model == "english"


# --- confidence honesty ----------------------------------------------------
def test_low_confidence_flagged_when_threshold_set():
    p = policy(min_confidence=0.6)
    answers = {"q": {"confidence": 0.4}, "r": {"confidence": 0.9}}
    out = p.annotate_confidence(answers)
    assert out["q"]["low_confidence"] is True
    assert out["q"]["confidence_threshold"] == 0.6
    assert "low_confidence" not in out["r"]


def test_no_flagging_when_threshold_zero():
    out = policy(min_confidence=0.0).annotate_confidence({"q": {"confidence": 0.1}})
    assert "low_confidence" not in out["q"]


# --- config parsing --------------------------------------------------------
def test_load_config_defaults(monkeypatch):
    for k in list(os.environ):
        if k.startswith("LAYA_"):
            monkeypatch.delenv(k, raising=False)
    c = load_config()
    assert c.models == ("english", "multilingual", "typed-decisions")
    assert c.allow_download is False  # offline by default
    assert c.default_model == "auto"


def test_load_config_rejects_bad_model(monkeypatch):
    monkeypatch.setenv("LAYA_MODELS", "english,bogus")
    with pytest.raises(ValueError, match="Invalid LAYA_MODELS"):
        load_config()


def test_load_config_rejects_bad_default(monkeypatch):
    monkeypatch.delenv("LAYA_MODELS", raising=False)
    monkeypatch.setenv("LAYA_DEFAULT_MODEL", "nope")
    with pytest.raises(ValueError, match="Invalid LAYA_DEFAULT_MODEL"):
        load_config()


def test_load_config_allow_download(monkeypatch):
    monkeypatch.setenv("LAYA_ALLOW_DOWNLOAD", "true")
    assert load_config().allow_download is True
