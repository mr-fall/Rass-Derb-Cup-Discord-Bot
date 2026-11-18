"""Runtime configuration loaded from Replit Secrets and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    guild_id: int | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        token = os.getenv("TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "Missing TOKEN. Add the Discord bot token as a Replit Secret named TOKEN."
            )

        raw_guild_id = os.getenv("GUILD_ID", "").strip()
        if not raw_guild_id:
            return cls(token=token)

        try:
            guild_id = int(raw_guild_id)
        except ValueError as error:
            raise RuntimeError("GUILD_ID must be a numeric Discord server ID.") from error

        if guild_id <= 0:
            raise RuntimeError("GUILD_ID must be a positive Discord server ID.")

        return cls(token=token, guild_id=guild_id)
