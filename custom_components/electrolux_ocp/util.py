"""Kleine Hilfsfunktionen ohne Home-Assistant-Abhängigkeiten."""

from __future__ import annotations

import re

# JWT (eyJ...) — Access-/Refresh-Tokens der OCP-API sind JWTs.
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
# "Bearer <token>" in Fehlertexten/Headern.
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]+")
# Generische lange Token-/Key-artige Zeichenketten (API Key etc.).
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{32,}\b")


def scrub_secrets(text: str) -> str:
    """Entferne token-/schlüsselartige Muster aus einem Freitext.

    Dient dazu, rohe Fremd-Exception-Strings vor dem (Debug-)Logging zu
    entschärfen, damit keine Access-/Refresh-Tokens oder API-Keys im Log landen.
    """
    if not text:
        return text
    text = _JWT_RE.sub("***", text)
    text = _BEARER_RE.sub("Bearer ***", text)
    text = _LONG_TOKEN_RE.sub("***", text)
    return text
