"""Structured extraction with a confidence score per field.

This demo uses a small deterministic extractor so the project runs
without an API key. Swap `_mock_extract` for an LLM call with
JSON schema when you wire OpenAI / Anthropic / Mistral.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


CATEGORIES = ("billing", "cancellation", "appointment", "general")


@dataclass
class Field:
    value: str
    confidence: float


@dataclass
class ExtractedCase:
    language: Field
    category: Field
    intent: Field
    summary: Field
    customer_name: Field
    urgency: Field
    fields: dict[str, Field] = field(default_factory=dict)

    def as_plain(self) -> dict:
        return {
            "language": self.language.value,
            "category": self.category.value,
            "intent": self.intent.value,
            "summary": self.summary.value,
            "customer_name": self.customer_name.value,
            "urgency": self.urgency.value,
        }

    def confidences(self) -> dict[str, float]:
        return {
            "language": self.language.confidence,
            "category": self.category.confidence,
            "intent": self.intent.confidence,
            "summary": self.summary.confidence,
            "customer_name": self.customer_name.confidence,
            "urgency": self.urgency.confidence,
        }


def detect_language(text: str) -> Field:
    t = text.lower()
    if re.search(r"\b(ich|kündigen|vertrag|termin|bitte)\b", t):
        return Field("de", 0.86)
    if re.search(r"\b(dua|termin|fatur|ju lutem|kontrata)\b", t):
        return Field("sq", 0.84)
    if re.search(r"\b(the|please|cancel|invoice|appointment)\b", t):
        return Field("en", 0.9)
    return Field("en", 0.45)


def extract(text: str) -> ExtractedCase:
    language = detect_language(text)
    t = text.lower()

    category, cat_conf = Field("general", 0.5), 0.5
    intent = "open_request"
    if re.search(r"kündig|cancel|anullo", t):
        category, cat_conf = Field("cancellation", 0.88), 0.88
        intent = "cancel_contract"
    elif re.search(r"invoice|bill|fatur|rechnung", t):
        category, cat_conf = Field("billing", 0.87), 0.87
        intent = "billing_question"
    elif re.search(r"appointment|termin", t):
        category, cat_conf = Field("appointment", 0.9), 0.9
        intent = "book_appointment"
    else:
        category = Field("general", 0.55)
        cat_conf = 0.55

    name_match = re.search(
        r"\b(?:i am|ich heisse|unë jam|une jam)\s+([A-Za-zÄÖÜäöüß]+)",
        text,
        flags=re.IGNORECASE,
    )
    name = Field(name_match.group(1), 0.8) if name_match else Field("", 0.2)

    urgency_val, urg_conf = "normal", 0.7
    if re.search(r"urgent|sofort|sa më shpejt|asap", t):
        urgency_val, urg_conf = "high", 0.85

    summary = Field(re.sub(r"\s+", " ", text).strip()[:180], 0.75)

    return ExtractedCase(
        language=language,
        category=category,
        intent=Field(intent, cat_conf),
        summary=summary,
        customer_name=name,
        urgency=Field(urgency_val, urg_conf),
    )
