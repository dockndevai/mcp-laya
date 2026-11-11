"""Security / policy engine — pure logic, no I/O, no torch. Fully unit-testable.

laya is read-only inference, so this engine does not gate mutations; it enforces the things that
actually matter for a local decision model: the model allowlist, request-size caps, confidence
honesty, and keeping the input text out of logs. Every request is audited, including the ones it
refuses.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, NoReturn

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

    @staticmethod
    def _questions_len(questions: dict[str, Any] | None) -> int:
        """Serialized size of the questions (their instructions, criteria and labels)."""
        if not questions:
            return 0
        return SecurityPolicy._state_len(questions)

    def reject(
        self,
        tool: str,
        state: Any,
        reason: str,
        *,
        model: str | None = None,
        questions: dict[str, Any] | None = None,
    ) -> NoReturn:
        """Audit a refused request, then raise PolicyError(reason)."""
        self.audit(
            tool,
            model=model,
            state_chars=self._state_len(state),
            questions=list((questions or {}).keys()),
            outcome="rejected",
            reason=reason,
        )
        raise PolicyError(reason)

    def guard(
        self, tool: str, state: Any, questions: dict[str, Any] | None, model: str | None
    ) -> GuardResult:
        try:
            resolved = self.resolve_model(model)
        except PolicyError as e:
            self.reject(tool, state, str(e), model=model, questions=questions)

        n = self._state_len(state)
        if n == 0:
            self.reject(tool, state, "Empty state — provide the text/JSON to evaluate.",
                        model=resolved, questions=questions)
        if n > self.config.max_input_chars:
            self.reject(
                tool, state,
                f"State is {n} chars, over the LAYA_MAX_INPUT_CHARS limit of "
                f"{self.config.max_input_chars}.",
                model=resolved, questions=questions,
            )
        if questions is not None:
            if not questions:
                self.reject(tool, state, "No questions provided.", model=resolved)
            if len(questions) > self.config.max_questions:
                self.reject(
                    tool, state,
                    f"{len(questions)} questions, over the LAYA_MAX_QUESTIONS limit of "
                    f"{self.config.max_questions}.",
                    model=resolved, questions=questions,
                )
            qn = self._questions_len(questions)
            if qn > self.config.max_input_chars:
                self.reject(
                    tool, state,
                    f"Questions are {qn} chars serialized, over the LAYA_MAX_INPUT_CHARS limit of "
                    f"{self.config.max_input_chars}.",
                    model=resolved, questions=questions,
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
    def audit(
        self,
        tool: str,
        *,
        model: str | None,
        state_chars: int,
        questions: list[str],
        outcome: str = "allowed",
        reason: str | None = None,
    ) -> None:
        if not self.config.audit_log:
            return
        line: dict[str, Any] = {
            "audit": "laya-mcp",
            "tool": tool,
            "outcome": outcome,
            "model": (model or "auto")[:64],
            "state_chars": state_chars,
            # Bound the line: a refused request may carry arbitrarily many / arbitrarily long ids.
            "questions": [str(q)[:64] for q in questions[: self.config.max_questions]],
            "state_redacted": self.config.redact_state,
        }
        if reason is not None:
            # The policy message may echo caller-supplied values (a model name); bound its size.
            line["reason"] = reason[:300]
        sys.stderr.write(json.dumps(line) + "\n")
