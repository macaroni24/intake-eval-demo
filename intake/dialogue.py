"""Tiny multilingual clarification before handing to a person."""

from __future__ import annotations

QUESTIONS = {
    "en": "Could you share your full name and what you need us to do?",
    "de": "Könnten Sie Ihren vollen Namen und Ihr Anliegen nennen?",
    "sq": "A mund të na jepni emrin tuaj të plotë dhe çfarë kërkoni?",
}

HANDOVER = {
    "en": "A teammate will review this case before anything is sent to the customer.",
    "de": "Eine Kollegin oder ein Kollege prüft den Fall, bevor etwas an den Kunden geht.",
    "sq": "Një koleg do ta shqyrtojë këtë rast para se t’i dërgohet klientit.",
}


def clarification(language: str, missing: list[str]) -> str | None:
    if not missing:
        return None
    return QUESTIONS.get(language, QUESTIONS["en"])


def handover_note(language: str) -> str:
    return HANDOVER.get(language, HANDOVER["en"])
