"""Security / policy engine — pure logic, no I/O, no torch. Fully unit-testable.

laya is read-only inference, so this engine does not gate mutations; it enforces the things that
actually matter for a local decision model: the model allowlist, request-size caps, confidence
honesty, and keeping the input text out of logs.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from .config import Config


class PolicyError(Exception):
    """Raised when a request violates the configured policy."""


@dataclass(frozen=True)
class GuardResult:
    model: str | None  # the checkpoint requested, or None to let the Router choose
    state_chars: int


class SecurityPolicy:
    def __init__(self, config: Config) -> None:
        self.config = config

    # --- model allowlist ---------------------------------------------------
    def is_model_allowed(self, model: str) -> bool:
        return model in self.config.models

    def resolve_model(self, requested: str | None) -> str | None:
        """Return the checkpoint to use, or None for the Router. Raises if not allowed."""
        model = (requested or self.config.default_model or "auto").strip().lower()
        if model == "auto":
            return None
        if not self.is_model_allowed(model):
            raise PolicyError(
                f"Model '{model}' is not permitted (LAYA_MODELS={','.join(self.config.models)})."
            )
        return model

    # --- request bounds ----------------------------------------------------
    @staticmethod
    def _state_len(state: Any) -> int:
        if isinstance(state, str):
            return len(state)
        try:
            return len(json.dumps(state, ensure_ascii=False))
        except (TypeError, ValueError):
            return len(str(state))

    def guard(
        self, tool: str, state: Any, questions: dict[str, Any] | None, model: str | None
    ) -> GuardResult:
        resolved = self.resolve_model(model)

        n = self._state_len(state)
        if n == 0:
            raise PolicyError("Empty state — provide the text/JSON to evaluate.")
        if n > self.config.max_input_chars:
            raise PolicyError(
                f"State is {n} chars, over the LAYA_MAX_INPUT_CHARS limit of "
                f"{self.config.max_input_chars}."
            )
        if questions is not None:
            if not questions:
                raise PolicyError("No questions provided.")
            if len(questions) > self.config.max_questions:
                raise PolicyError(
                    f"{len(questions)} questions, over the LAYA_MAX_QUESTIONS limit of "
                    f"{self.config.max_questions}."
                )

        self.audit(tool, model=resolved, state_chars=n, questions=list((questions or {}).keys()))
        return GuardResult(model=resolved, state_chars=n)

    # --- confidence honesty ------------------------------------------------
    def annotate_confidence(self, answers: dict[str, Any]) -> dict[str, Any]:
        """Flag (never drop) answers whose confidence is below LAYA_MIN_CONFIDENCE."""
        thr = self.config.min_confidence
        if thr <= 0:
            return answers
        for a in answers.values():
            if isinstance(a, dict):
                conf = a.get("confidence")
                if isinstance(conf, (int, float)) and conf < thr:
                    a["low_confidence"] = True
                    a["confidence_threshold"] = thr
        return answers

    # --- audit -------------------------------------------------------------
    def audit(self, tool: str, *, model: str | None, state_chars: int, questions: list[str]) -> None:
        if not self.config.audit_log:
            return
        line = {
            "audit": "laya-mcp",
            "tool": tool,
            "model": model or "auto",
            "state_chars": state_chars,
            "questions": questions,
            "state_redacted": self.config.redact_state,
        }
        sys.stderr.write(json.dumps(line) + "\n")
