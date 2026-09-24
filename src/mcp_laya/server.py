"""The mcp-laya server: fast, local, typed decisions for agents, exposed as MCP tools.

Every tool is read-only inference — laya reads a state and returns a typed decision with calibrated
confidence in a single forward pass (~33 ms), in 100+ languages, with no text generation (nothing to
parse, nothing to hallucinate). Guardrails live in security.py; the model runs locally and offline by
default (see config.py).
"""
from __future__ import annotations

from typing import Any, NoReturn

from mcp.server.mcpserver import MCPServer

from .config import load_config
from .engine import EngineError, LayaEngine
from .security import PolicyError, SecurityPolicy

_config = load_config()
_policy = SecurityPolicy(_config)
_engine = LayaEngine(_config)

mcp = MCPServer("laya")

State = str | dict[str, Any]


def _fail(e: Exception) -> NoReturn:
    """Surface a clean, single-line error to the host (marked as a tool error)."""
    if isinstance(e, (PolicyError, EngineError)):
        raise RuntimeError(str(e)) from None
    raise e


@mcp.tool()
def decide(state: State, questions: dict[str, dict[str, Any]], model: str | None = None) -> dict[str, Any]:
    """Answer several typed questions about a state in one local forward pass.

    Use this to offload System-1 judgment calls from the main model: classification, routing,
    scoring and yes/no gates over text, an email, a ticket or a JSON object — fast, local, and
    without hallucination. Each question is one of three types:

    - choice: {"type":"choice","instructions":"...","criteria":{"labelA":"desc","labelB":"desc"}}
    - score:  {"type":"score","instructions":"...","criteria":["level0","level1","level2"]}
    - noul:   {"type":"noul","instructions":"..."}   (yes/no/unknown)

    Returns every answer with its calibrated `confidence` and full probabilities, plus `routing`
    metadata explaining which checkpoint answered. `model` optionally pins english | multilingual |
    typed-decisions (default: the Router auto-selects per language/task).
    """
    try:
        g = _policy.guard("decide", state, questions, model)
        result = _engine.decide(state, questions, g.model)
        result["answers"] = _policy.annotate_confidence(result.get("answers", {}))
        return result
    except Exception as e:
        _fail(e)


@mcp.tool()
def classify(
    state: State,
    labels: list[str] | None = None,
    criteria: dict[str, str] | None = None,
    instructions: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Assign the single best category to a state (one `choice` question).

    Provide either `labels` (a list of category names) or `criteria` (a map of category -> short
    description; more accurate). Returns the chosen label, calibrated confidence, and the probability
    over all labels.
    """
    try:
        if not criteria and not labels:
            raise PolicyError("Provide either `labels` or `criteria`.")
        crit = criteria or {label: label for label in (labels or [])}
        q = {
            "result": {
                "type": "choice",
                "instructions": instructions or "Choose the best category.",
                "criteria": crit,
            }
        }
        g = _policy.guard("classify", state, q, model)
        answers = _policy.annotate_confidence(_engine.decide(state, q, g.model).get("answers", {}))
        return answers.get("result", {})
    except Exception as e:
        _fail(e)


@mcp.tool()
def score(
    state: State,
    instructions: str,
    levels: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    """Rate a state on an ordinal scale (one `score` question).

    `levels` are the ordered rungs, lowest first, e.g. ["not urgent","soon","critical"]. Returns an
    expected score (0..len-1), the level legend, calibrated confidence, and per-level probabilities.
    """
    try:
        if len(levels) < 2:
            raise PolicyError("Provide at least two ordered `levels`.")
        q = {"result": {"type": "score", "instructions": instructions, "criteria": levels}}
        g = _policy.guard("score", state, q, model)
        answers = _policy.annotate_confidence(_engine.decide(state, q, g.model).get("answers", {}))
        return answers.get("result", {})
    except Exception as e:
        _fail(e)


@mcp.tool()
def check(state: State, instructions: str, model: str | None = None) -> dict[str, Any]:
    """Answer a single yes/no/unknown question about a state (a `noul` gate).

    Returns `answer` (yes | no), the probability of yes (0..1), and calibrated confidence. Ideal for
    agent control flow: "does the user request a refund?", "is this a security incident?".
    """
    try:
        q = {"result": {"type": "noul", "instructions": instructions}}
        g = _policy.guard("check", state, q, model)
        answers = _policy.annotate_confidence(_engine.decide(state, q, g.model).get("answers", {}))
        a = answers.get("result", {})
        p_yes = a.get("noul")
        if isinstance(p_yes, (int, float)):
            a["answer"] = "yes" if p_yes >= 0.5 else "no"
            a["probability_yes"] = p_yes
        return a
    except Exception as e:
        _fail(e)


@mcp.tool()
def triage(state: State, preset: str = "triage", model: str | None = None) -> dict[str, Any]:
    """Run a ready-made set of decisions over a state using a laya preset.

    presets: triage (department/urgency/sentiment…), email, moderation (safety categories), guard
    (prompt-injection / policy gates). Returns all answers with confidence.
    """
    try:
        questions = _engine.preset_questions(preset)
        g = _policy.guard(f"triage:{preset}", state, questions, model)
        result = _engine.decide(state, questions, g.model)
        result["answers"] = _policy.annotate_confidence(result.get("answers", {}))
        return result
    except Exception as e:
        _fail(e)


@mcp.tool()
def detect_language(text: str) -> dict[str, Any]:
    """Detect the script and language of a text (sub-millisecond, no model forward pass)."""
    try:
        _policy.guard("detect_language", text, None, None)
        return _engine.detect_language(text)
    except Exception as e:
        _fail(e)


@mcp.tool()
def explain_routing(state: State, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Explain which checkpoint the Router would use for this state, without running inference."""
    try:
        _policy.guard("explain_routing", state, questions, None)
        return _engine.explain_routing(state, questions)
    except Exception as e:
        _fail(e)


@mcp.tool()
def list_models() -> dict[str, Any]:
    """List the laya checkpoints this server may use, the default, device and offline status."""
    return _engine.list_models()
