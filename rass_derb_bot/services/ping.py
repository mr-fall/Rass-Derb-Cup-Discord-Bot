"""Formatting helpers for the bot's latency response."""

from __future__ import annotations


def format_ping(latency_seconds: float) -> str:
    """Return a concise latency response in milliseconds."""
    latency_ms = max(0, round(latency_seconds * 1000))
    return f"Pong — {latency_ms} ms"

