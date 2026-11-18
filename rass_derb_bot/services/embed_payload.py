"""Parse and validate user-provided JSON into Discord message objects."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import discord

EMBED_KEYS = {
    "author",
    "color",
    "description",
    "fields",
    "footer",
    "image",
    "image_url",
    "thumbnail",
    "timestamp",
    "title",
    "url",
}
ALLOWED_TOP_LEVEL_KEYS = {"content", "embeds", *EMBED_KEYS}
MAX_EMBEDS = 10
MAX_CONTENT_LENGTH = 2000
MAX_EMBED_LENGTH = 6000


class EmbedPayloadError(ValueError):
    """Raised when a custom embed payload is invalid or exceeds Discord limits."""


def parse_embed_payload(raw_payload: str) -> tuple[str | None, list[discord.Embed]]:
    """Convert a JSON message payload to content and Discord embeds."""
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as error:
        raise EmbedPayloadError(
            f"JSON syntax error on line {error.lineno}, column {error.colno}."
        ) from error

    if not isinstance(payload, dict):
        raise EmbedPayloadError("the top-level JSON value must be an object.")

    unknown_keys = set(payload) - ALLOWED_TOP_LEVEL_KEYS
    if unknown_keys:
        names = ", ".join(sorted(unknown_keys))
        raise EmbedPayloadError(f"unsupported top-level key(s): {names}.")

    content = payload.get("content")
    if content is not None and not isinstance(content, str):
        raise EmbedPayloadError("'content' must be a string.")
    if isinstance(content, str) and len(content) > MAX_CONTENT_LENGTH:
        raise EmbedPayloadError("'content' exceeds Discord's 2,000-character limit.")

    if "embeds" in payload and EMBED_KEYS.intersection(payload):
        raise EmbedPayloadError(
            "use either the 'embeds' array or top-level embed fields, not both."
        )

    if "embeds" in payload:
        raw_embeds = payload["embeds"]
        if not isinstance(raw_embeds, list):
            raise EmbedPayloadError("'embeds' must be an array.")
    elif EMBED_KEYS.intersection(payload):
        raw_embeds = [{key: value for key, value in payload.items() if key != "content"}]
    else:
        raw_embeds = []

    if len(raw_embeds) > MAX_EMBEDS:
        raise EmbedPayloadError("Discord allows no more than 10 embeds per message.")

    embeds = [
        _build_embed(embed_data, index)
        for index, embed_data in enumerate(raw_embeds, start=1)
    ]
    if not content and not embeds:
        raise EmbedPayloadError("include 'content', at least one embed, or both.")
    return content, embeds


def _build_embed(raw_embed: Any, index: int) -> discord.Embed:
    if not isinstance(raw_embed, Mapping):
        raise EmbedPayloadError(f"embed {index} must be a JSON object.")

    embed_data = dict(raw_embed)
    if "image_url" in embed_data:
        if "image" in embed_data:
            raise EmbedPayloadError(
                f"embed {index} cannot contain both 'image' and 'image_url'."
            )
        embed_data["image"] = {"url": embed_data.pop("image_url")}

    _normalize_color(embed_data, index)
    _validate_embed_urls(embed_data, index)

    try:
        embed = discord.Embed.from_dict(embed_data)
    except (TypeError, ValueError, AttributeError) as error:
        raise EmbedPayloadError(f"embed {index} has an invalid field: {error}.") from error

    if not any(
        (
            embed.title,
            embed.description,
            embed.url,
            embed.author.name,
            embed.footer.text,
            embed.fields,
            embed.image.url,
            embed.thumbnail.url,
        )
    ):
        raise EmbedPayloadError(f"embed {index} has no displayable content.")

    if len(embed.fields) > 25:
        raise EmbedPayloadError(f"embed {index} has more than 25 fields.")
    for field_number, field in enumerate(embed.fields, start=1):
        if not field.name or len(field.name) > 256:
            raise EmbedPayloadError(
                f"embed {index} field {field_number} needs a name of 1–256 characters."
            )
        if not field.value or len(field.value) > 1024:
            raise EmbedPayloadError(
                f"embed {index} field {field_number} needs a value of 1–1,024 characters."
            )
    if embed.title and len(embed.title) > 256:
        raise EmbedPayloadError(f"embed {index} title exceeds 256 characters.")
    if embed.description and len(embed.description) > 4096:
        raise EmbedPayloadError(f"embed {index} description exceeds 4,096 characters.")
    if embed.footer.text and len(embed.footer.text) > 2048:
        raise EmbedPayloadError(f"embed {index} footer exceeds 2,048 characters.")
    if embed.author.name and len(embed.author.name) > 256:
        raise EmbedPayloadError(f"embed {index} author name exceeds 256 characters.")
    if len(embed) > MAX_EMBED_LENGTH:
        raise EmbedPayloadError(
            f"embed {index} exceeds Discord's 6,000-character text limit."
        )

    return embed


def _normalize_color(embed_data: dict[str, Any], index: int) -> None:
    color = embed_data.get("color")
    if color is None:
        return
    if isinstance(color, bool):
        raise EmbedPayloadError(f"embed {index} color must be an integer or hex string.")
    if isinstance(color, int):
        if not 0 <= color <= 0xFFFFFF:
            raise EmbedPayloadError(
                f"embed {index} color must be between 0 and 16777215."
            )
        return
    if not isinstance(color, str):
        raise EmbedPayloadError(f"embed {index} color must be an integer or hex string.")

    hex_color = color.removeprefix("#")
    if len(hex_color) != 6:
        raise EmbedPayloadError(
            f"embed {index} hex color must use six digits, such as '#2E86DE'."
        )
    try:
        embed_data["color"] = int(hex_color, 16)
    except ValueError as error:
        raise EmbedPayloadError(
            f"embed {index} color must be a six-digit hex value, such as '#2E86DE'."
        ) from error


def _validate_embed_urls(embed_data: dict[str, Any], index: int) -> None:
    url_values: list[tuple[str, Any]] = []
    if "url" in embed_data:
        url_values.append(("url", embed_data["url"]))
    for key in ("image", "thumbnail", "author", "footer"):
        value = embed_data.get(key)
        url_key = {"image": "url", "thumbnail": "url", "author": "url", "footer": "icon_url"}[key]
        if isinstance(value, Mapping) and url_key in value:
            url_values.append((f"{key}.{url_key}", value[url_key]))
        elif key in {"image", "thumbnail"} and isinstance(value, str):
            url_values.append((f"{key}.url", value))
            embed_data[key] = {"url": value}

    for key, url in url_values:
        if not isinstance(url, str):
            raise EmbedPayloadError(f"embed {index} {key} must be a URL string.")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise EmbedPayloadError(
                f"embed {index} {key} must be a full http:// or https:// URL."
            )

    timestamp = embed_data.get("timestamp")
    if timestamp is not None:
        if not isinstance(timestamp, str):
            raise EmbedPayloadError(f"embed {index} timestamp must be an ISO-8601 string.")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise EmbedPayloadError(
                f"embed {index} timestamp must be a valid ISO-8601 date and time."
            ) from error

