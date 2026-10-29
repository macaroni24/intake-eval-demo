"""Intake pipeline: safety → extract → safety → human queue.

Tracks latency. Cost is 0 in the mock extractor; keep the field so
an LLM swap does not change the result shape.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .dialogue import clarification, handover_note
from .extract import ExtractedCase, extract
from .safety import SafetyResult, post_check, pre_check


@dataclass
class IntakeResult:
    status: str
    reason: str
    extracted: ExtractedCase | None
    pre_safety: SafetyResult
    post_safety: SafetyResult | None
    clarification: str | None
    handover: str | None
    latency_ms: int
    cost_usd: float

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "extracted": None
            if self.extracted is None
            else {
                "fields": self.extracted.as_plain(),
                "confidence": self.extracted.confidences(),
            },
            "pre_safety": self.pre_safety.to_dict(),
            "post_safety": None if self.post_safety is None else self.post_safety.to_dict(),
            "clarification": self.clarification,
            "handover": self.handover,
            "metrics": {"latency_ms": self.latency_ms, "cost_usd": self.cost_usd},
        }


def run_intake(text: str) -> IntakeResult:
    started = time.perf_counter()
    pre = pre_check(text)

    if any(h.kind == "emergency" for h in pre.hits):
        return _done(
            started,
            status="escalate_emergency",
            reason="Emergency pattern matched before the model.",
            pre=pre,
            extracted=None,
            post=None,
            language="en",
            need_clarify=False,
        )

    if any(h.kind == "blocked" for h in pre.hits):
        return _done(
            started,
            status="blocked",
            reason="Blocked topic matched before the model.",
            pre=pre,
            extracted=None,
            post=None,
            language="en",
            need_clarify=False,
        )

    if any(h.kind == "injection" for h in pre.hits):
        return _done(
            started,
            status="blocked",
            reason="Prompt-injection pattern matched; untrusted input was not sent to the model.",
            pre=pre,
            extracted=None,
            post=None,
            language="en",
            need_clarify=False,
        )

    extracted = extract(text)
    post = post_check(extracted.as_plain())
    if not post.ok:
        return _done(
            started,
            status="blocked",
            reason="Post-model safety check failed.",
            pre=pre,
            extracted=extracted,
            post=post,
            language=extracted.language.value,
            need_clarify=False,
        )

    missing = [name for name, conf in extracted.confidences().items() if conf < 0.6]
    need_clarify = "customer_name" in missing or extracted.category.confidence < 0.6
    status = "needs_clarification" if need_clarify else "awaiting_human_approval"
    reason = (
        "Low-confidence fields; ask one clarifying question."
        if need_clarify
        else "Ready for human approval. Nothing is auto-sent."
    )
    return _done(
        started,
        status=status,
        reason=reason,
        pre=pre,
        extracted=extracted,
        post=post,
        language=extracted.language.value,
        need_clarify=need_clarify,
    )


def _done(
    started: float,
    *,
    status: str,
    reason: str,
    pre: SafetyResult,
    extracted: ExtractedCase | None,
    post: SafetyResult | None,
    language: str,
    need_clarify: bool,
) -> IntakeResult:
    missing = []
    if extracted and extracted.customer_name.confidence < 0.6:
        missing.append("customer_name")
    return IntakeResult(
        status=status,
        reason=reason,
        extracted=extracted,
        pre_safety=pre,
        post_safety=post,
        clarification=clarification(language, missing) if need_clarify else None,
        handover=handover_note(language) if status == "awaiting_human_approval" else None,
        latency_ms=int((time.perf_counter() - started) * 1000),
        cost_usd=0.0,
    )
