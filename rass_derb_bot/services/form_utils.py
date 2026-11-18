"""Validation and conversion helpers for form commands."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


MESSAGE_LINK_RE = re.compile(r"^/channels/(\d+)/(\d+)/(\d+)/?$")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$")


class FormInputError(ValueError):
    """Raised for invalid form configuration input."""


def validate_slug(value: str) -> str:
    slug = value.strip().lower()
    if not SLUG_RE.fullmatch(slug):
        raise FormInputError(
            "Use 1–50 lowercase letters, numbers, hyphens, or underscores."
        )
    return slug


def parse_color(value: str) -> int:
    color = value.strip().removeprefix("#")
    if len(color) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", color):
        raise FormInputError("Enter a six-digit hex color such as #2E86DE.")
    return int(color, 16)


def validate_image_url(value: str) -> str | None:
    image_url = value.strip()
    if not image_url:
        return None
    parsed = urlsplit(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FormInputError("Enter a full image URL starting with http:// or https://.")
    return image_url


def parse_message_link(value: str) -> tuple[int, int, int]:
    parts = urlsplit(value.strip())
    if (
        parts.scheme != "https"
        or parts.hostname
        not in {"discord.com", "www.discord.com", "canary.discord.com", "ptb.discord.com"}
    ):
        raise FormInputError("Use a full Discord message link starting with https://discord.com.")

    match = MESSAGE_LINK_RE.fullmatch(parts.path)
    if not match:
        raise FormInputError(
            "The link must look like https://discord.com/channels/server/channel/message."
        )
    return tuple(int(part) for part in match.groups())

