"""Bot client setup, extension loading, and slash-command synchronization."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiosqlite
import asyncpg
import discord
from discord.ext import commands

from rass_derb_bot.config import Settings
from rass_derb_bot.services.forms_repository import FormsRepository
from rass_derb_bot.services.sqlite_forms_repository import SQLiteFormsRepository

logger = logging.getLogger(__name__)


class RassDerbBot(commands.Bot):
    """Central bot client; feature modules are loaded as extensions."""

    EXTENSIONS = (
        "rass_derb_bot.cogs.embed",
        "rass_derb_bot.cogs.ping",
        "rass_derb_bot.cogs.form_admin",
        "rass_derb_bot.cogs.form_editor",
        "rass_derb_bot.cogs.help",
        "rass_derb_bot.cogs.music",
    )

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents)
        self.settings = settings
        self._persistent_views: list[discord.ui.View] = []
        self.db_pool: asyncpg.Pool | None = None
        self.forms: Any = None

        self._register_prefix_commands()

    def _register_prefix_commands(self) -> None:
        @self.command(name="sync")
        @commands.has_permissions(manage_guild=True)
        async def sync_cmd(ctx: commands.Context) -> None:
            if ctx.guild:
                # Clear guild-level commands to prevent duplicates with global commands
                self.tree.clear_commands(guild=ctx.guild)
                await self.tree.sync(guild=ctx.guild)
            synced = await self.tree.sync()
            await ctx.send(f"✅ Synchronized {len(synced)} commands.")

    def register_persistent_view(self, view: discord.ui.View) -> None:
        """Queue a timeout-free view for registration after extensions load."""
        if view.timeout is not None:
            raise ValueError("Persistent views must use timeout=None.")
        self._persistent_views.append(view)

    async def setup_hook(self) -> None:
        await super().setup_hook()

        use_sqlite = False
        db_url = self.settings.database_url.lower()

        if "helium" in db_url or db_url.startswith("sqlite"):
            logger.warning(
                "DATABASE_URL contains Replit-internal 'helium' or SQLite URL. "
                "Using local SQLite database 'rass_derb.db' automatically."
            )
            use_sqlite = True
        else:
            try:
                self.db_pool = await asyncpg.create_pool(
                    dsn=self.settings.database_url,
                    min_size=1,
                    max_size=5,
                )
                self.forms = FormsRepository(self.db_pool)
                await self.forms.init_db()
                logger.info("Connected to PostgreSQL database successfully.")
            except Exception as e:
                logger.warning(
                    "Could not connect to PostgreSQL (%s). Falling back to local SQLite database.",
                    e,
                )
                use_sqlite = True

        if use_sqlite:
            db_path = Path("rass_derb.db").resolve()
            sqlite_conn = await aiosqlite.connect(db_path)
            sqlite_conn.row_factory = aiosqlite.Row
            self.forms = SQLiteFormsRepository(sqlite_conn)
            await self.forms.init_db()
            logger.info("Initialized local SQLite database at: %s", db_path)

        await self._remove_legacy_embed_command()

        for extension in self.EXTENSIONS:
            await self.load_extension(extension)
            logger.info("Loaded extension: %s", extension)

        for view in self._persistent_views:
            self.add_view(view)

        await self._restore_persistent_form_buttons()

        # Global sync
        synced = await self.tree.sync()
        logger.info("Synchronized %d global application command(s).", len(synced))

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id if self.user else "None")
        # Clean up any leftover guild-level commands in all guilds to eliminate duplicates
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info("Removed duplicate guild commands from '%s' (%d)", guild.name, guild.id)
            except Exception as e:
                logger.debug("Could not clean guild commands in '%s': %s", guild.name, e)

    async def _remove_legacy_embed_command(self) -> None:
        guild_id = self.settings.legacy_guild_id
        if guild_id is None:
            return

        guild = discord.Object(id=guild_id)
        old_commands = await self.tree.fetch_commands(guild=guild)
        duplicates = [command for command in old_commands if command.name == "embed"]
        for command in duplicates:
            await command.delete()
        if duplicates:
            logger.info(
                "Removed %d obsolete server-specific /embed command(s).",
                len(duplicates),
            )

    async def _restore_persistent_form_buttons(self) -> None:
        if self.forms is None:
            return

        from rass_derb_bot.ui.form_button import FormButtonView

        buttons = await self.forms.list_active_buttons()
        for button in buttons:
            view = FormButtonView(self, button)
            self.add_view(view, message_id=int(button["message_id"]))
        logger.info("Restored %d persistent form button(s).", len(buttons))

    async def close(self) -> None:
        await super().close()
        if self.db_pool is not None:
            await self.db_pool.close()
            self.db_pool = None
        if hasattr(self.forms, "close"):
            await self.forms.close()
        self.forms = None
