"""Configuration from environment variables.

mcp-laya wraps the local `laya` decision engine. laya only *reads* a state and returns typed
decisions — it never mutates anything — so the safe-by-default story here is different from the rest
of the suite: it is about privacy and resource control, not write gating.

- **Offline by default.** The model runs locally; nothing is sent anywhere. laya's checkpoints are
  fetched from Hugging Face the first time — that network access is the one thing that can "leave the
  box", so it is disabled unless LAYA_ALLOW_DOWNLOAD=true. Pre-fetch the models once, then run offline.
- **Model allowlist.** LAYA_MODELS pins which checkpoints may load.
- **Input caps.** LAYA_MAX_INPUT_CHARS / LAYA_MAX_QUESTIONS bound each request.
- **Confidence honesty.** LAYA_MIN_CONFIDENCE flags (never silently trusts) low-confidence answers.
- **Log privacy.** LAYA_REDACT_STATE keeps the input text out of the audit log by default.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

VALID_MODELS = ("english", "multilingual", "typed-decisions")


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    v = os.environ.get(name)
    try:
        return int(v) if v not in (None, "") else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    v = os.environ.get(name)
    try:
        return float(v) if v not in (None, "") else default
    except ValueError:
        return default


def _list(name: str) -> list[str]:
    v = os.environ.get(name, "")
    return [s.strip() for s in v.split(",") if s.strip()]


@dataclass(frozen=True)
class Config:
    models: tuple[str, ...] = VALID_MODELS
    default_model: str = "auto"  # "auto" = let laya's Router pick per request
    device: str = "auto"  # auto | cpu | cuda
    preload: bool = False
    allow_download: bool = False
    max_input_chars: int = 20_000
    max_questions: int = 32
    min_confidence: float = 0.0  # 0 = never flag; e.g. 0.6 flags answers below it
    audit_log: bool = True
    redact_state: bool = True
    hf_token: str | None = None
    extra: dict = field(default_factory=dict)


def load_config() -> Config:
    allowed = _list("LAYA_MODELS")
    models: tuple[str, ...]
    if allowed:
        bad = [m for m in allowed if m not in VALID_MODELS]
        if bad:
            raise ValueError(
                f"Invalid LAYA_MODELS {bad}. Valid checkpoints: {', '.join(VALID_MODELS)}."
            )
        models = tuple(allowed)
    else:
        models = VALID_MODELS

    default_model = (os.environ.get("LAYA_DEFAULT_MODEL") or "auto").strip().lower()
    if default_model not in ("auto", *VALID_MODELS):
        raise ValueError(
            f"Invalid LAYA_DEFAULT_MODEL '{default_model}'. Use 'auto' or one of {', '.join(VALID_MODELS)}."
        )

    device = (os.environ.get("LAYA_DEVICE") or "auto").strip().lower()
    if device not in ("auto", "cpu", "cuda"):
        raise ValueError(f"Invalid LAYA_DEVICE '{device}'. Use auto, cpu or cuda.")

    return Config(
        models=models,
        default_model=default_model,
        device=device,
        preload=_bool("LAYA_PRELOAD", False),
        allow_download=_bool("LAYA_ALLOW_DOWNLOAD", False),
        max_input_chars=max(1, _int("LAYA_MAX_INPUT_CHARS", 20_000)),
        max_questions=max(1, _int("LAYA_MAX_QUESTIONS", 32)),
        min_confidence=min(1.0, max(0.0, _float("LAYA_MIN_CONFIDENCE", 0.0))),
        audit_log=_bool("LAYA_AUDIT_LOG", True),
        redact_state=_bool("LAYA_REDACT_STATE", True),
        hf_token=(os.environ.get("HF_TOKEN") or None),
    )
