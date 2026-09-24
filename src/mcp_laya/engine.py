"""Thin wrapper over the `laya` library.

laya (and its torch/transformers stack) is imported lazily so the MCP server can start, advertise its
tools, and run the pure policy tests without loading a model. When LAYA_ALLOW_DOWNLOAD is false we set
the Hugging Face offline switches *before* importing laya, so a missing checkpoint fails fast with a
clear message instead of silently reaching out to the network.
"""
from __future__ import annotations

import os
from typing import Any

from .config import Config


class EngineError(Exception):
    """A problem loading a checkpoint or running inference."""


PRESETS = ("triage", "email", "moderation", "guard")


class LayaEngine:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._router: Any = None
        self._laya: Any = None

    # --- lazy loading ------------------------------------------------------
    def _import_laya(self) -> Any:
        if self._laya is not None:
            return self._laya
        if not self.config.allow_download:
            # Must be set before transformers / huggingface_hub are imported by laya.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        try:
            import laya
        except Exception as e:  # pragma: no cover - import-time env issue
            raise EngineError(
                "Could not import 'laya'. Install it with `pip install laya` (it pulls in torch)."
            ) from e
        self._laya = laya
        return laya

    def _get_router(self) -> Any:
        if self._router is not None:
            return self._router
        laya = self._import_laya()
        device = None if self.config.device == "auto" else self.config.device
        try:
            router = laya.Router(
                device=device,
                token=self.config.hf_token,
                preload=self.config.preload,
            )
        except Exception as e:
            raise self._download_hint(e)
        self._router = router
        return router

    def _download_hint(self, e: Exception) -> EngineError:
        if not self.config.allow_download:
            return EngineError(
                "A laya checkpoint is not available locally and downloads are disabled. "
                "Pre-fetch it once with `LAYA_ALLOW_DOWNLOAD=true`, or run "
                "`python -c \"import laya; laya.Router(preload=True)\"` with network access, "
                f"then run offline. Underlying error: {e}"
            )
        return EngineError(f"Failed to load a laya checkpoint: {e}")

    def warmup(self) -> None:
        """Force the router (and, if preload, the checkpoints) to load now."""
        self._get_router()

    # --- operations --------------------------------------------------------
    def decide(self, state: Any, questions: dict[str, Any], model: str | None) -> dict[str, Any]:
        router = self._get_router()
        try:
            return router.predict(state, questions, model=model)
        except Exception as e:
            raise self._download_hint(e) if "offline" in str(e).lower() else EngineError(str(e))

    def explain_routing(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        router = self._get_router()
        try:
            return dict(router.route(state, questions))
        except Exception as e:
            raise EngineError(str(e))

    def detect_language(self, text: str) -> dict[str, Any]:
        laya = self._import_laya()
        analysis = laya.detect_language(text)
        result = dict(analysis) if isinstance(analysis, dict) else {"analysis": analysis}
        try:
            result["is_english"] = bool(laya.is_english(text))
        except Exception:
            pass
        return result

    def preset_questions(self, preset: str, categories: dict[str, str] | None = None) -> dict[str, Any]:
        laya = self._import_laya()
        table = {
            "triage": laya.triage_questions,
            "email": laya.email_questions,
            "moderation": laya.moderation_questions,
            "guard": laya.guard_questions,
        }
        if preset not in table:
            raise EngineError(f"Unknown preset '{preset}'. Available: {', '.join(PRESETS)}.")
        if preset == "email" and categories:
            return laya.email_questions(categories)
        return table[preset]()

    def list_models(self) -> dict[str, Any]:
        return {
            "allowed": list(self.config.models),
            "default": self.config.default_model,
            "device": self.config.device,
            "offline": not self.config.allow_download,
            "checkpoints": {
                "english": "ModernBERT-large, 421M, 512 ctx — English",
                "multilingual": "mmBERT-base, 322M, 1024 ctx — 100+ languages, ~2x faster",
                "typed-decisions": "ModernBERT-large, 421M, 1024 ctx — typed-decision workflows",
            },
        }
