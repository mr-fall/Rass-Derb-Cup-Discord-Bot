"""Runtime configuration loaded from Replit Secrets and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_url: str
    guild_id: int | None = None
    legacy_guild_id: int | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        token = os.getenv("TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "Missing TOKEN. Add the Discord bot token as a Replit Secret named TOKEN."
            )

        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError(
                "Missing DATABASE_URL. Add the project's PostgreSQL connection as a Replit Secret."
            )

        guild_id = _optional_positive_id("GUILD_ID")
        legacy_guild_id = _optional_positive_id("LEGACY_GUILD_ID")
        return cls(
            token=token,
            database_url=database_url,
            guild_id=guild_id,
            legacy_guild_id=legacy_guild_id,
        )


def _optional_positive_id(name: str) -> int | None:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return None

    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a numeric Discord ID.") from error

    if value <= 0:
        raise RuntimeError(f"{name} must be a positive Discord ID.")
    return value
