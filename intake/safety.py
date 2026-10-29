"""Rule-based checks that run before and after the model.

Emergency, blocked topics, and prompt-injection heuristics stay
deterministic so they cannot be talked out of by the LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMERGENCY = [
    r"\b(emergency|ambulance|injured|on fire|heart attack)\b",
    r"\b(notfall|krankenwagen|verletzt|brand)\b",
    r"\b(emergjenc|lënduar|lenduara|zjarr)\b",
]

BLOCKED = [
    r"\b(tax evasion|money laundering|hide income)\b",
    r"\b(steuerhinterziehung|geldwäsche)\b",
    r"\b(shmangie tatimore)\b",
    r"\bhow to (make|build) a bomb\b",
]

INJECTION = [
    r"ignore (all )?previous instructions",
    r"you are now",
    r"system prompt",
    r"reveal (your |the )?hidden",
    r"<\|?(system|im_start)",
]


@dataclass
class SafetyHit:
    kind: str
    rule: str


@dataclass
class SafetyResult:
    ok: bool
    hits: list[SafetyHit]
    stage: str

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "stage": self.stage,
            "hits": [{"kind": h.kind, "rule": h.rule} for h in self.hits],
        }


def _scan(text: str, kind: str, patterns: list[str]) -> list[SafetyHit]:
    hits: list[SafetyHit] = []
    lowered = text.lower()
    for pattern in patterns:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            hits.append(SafetyHit(kind=kind, rule=pattern))
    return hits


def pre_check(text: str) -> SafetyResult:
    hits = (
        _scan(text, "emergency", EMERGENCY)
        + _scan(text, "blocked", BLOCKED)
        + _scan(text, "injection", INJECTION)
    )
    return SafetyResult(ok=len(hits) == 0, hits=hits, stage="pre_model")


def post_check(extracted: dict) -> SafetyResult:
    """Re-run rules on model output so a jailbreak cannot skip policy."""
    blob = " ".join(str(v) for v in extracted.values())
    hits = _scan(blob, "blocked", BLOCKED) + _scan(blob, "emergency", EMERGENCY)
    if extracted.get("category") == "blocked":
        hits.append(SafetyHit(kind="blocked", rule="category=blocked"))
    return SafetyResult(ok=len(hits) == 0, hits=hits, stage="post_model")
