"""Runtime configuration loaded from environment variables or .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Look for .env in common local and cloud container locations
possible_env_paths = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parents[1] / ".env",
    Path("/home/container/.env"),
    Path.cwd() / "env",
    Path.cwd() / ".env.txt",
    Path("/home/container/env"),
    Path("/home/container/.env.txt"),
]

try:
    from dotenv import load_dotenv
    loaded = False
    for env_path in possible_env_paths:
        if env_path.is_file():
            load_dotenv(env_path, override=True)
            loaded = True
            break
    if not loaded:
        load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_url: str
    guild_id: int | None = None
    legacy_guild_id: int | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        token = (
            os.getenv("TOKEN", "")
            or os.getenv("DISCORD_TOKEN", "")
            or os.getenv("BOT_TOKEN", "")
        ).strip()

        if not token:
            try:
                files = [f.name for f in Path.cwd().iterdir() if f.is_file()]
            except Exception:
                files = []
            raise RuntimeError(
                f"Missing TOKEN. Current folder ({Path.cwd()}) contains: {files}. "
                "Please create a file named '.env' with: TOKEN=your_bot_token"
            )

        database_url = os.getenv("DATABASE_URL", "").strip() or "sqlite:///rass_derb.db"

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
