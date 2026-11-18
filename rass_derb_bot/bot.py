"""Bot client setup, extension loading, and slash-command synchronization."""

from __future__ import annotations

import logging

import asyncpg
import discord
from discord.ext import commands

from rass_derb_bot.config import Settings
from rass_derb_bot.services.forms_repository import FormsRepository

logger = logging.getLogger(__name__)


class RassDerbBot(commands.Bot):
    """Central bot client; feature modules are loaded as extensions."""

    EXTENSIONS = (
        "rass_derb_bot.cogs.embed",
        "rass_derb_bot.cogs.ping",
        "rass_derb_bot.cogs.form_admin",
        "rass_derb_bot.cogs.form_editor",
        "rass_derb_bot.cogs.help",
    )

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        # Enabled to match the bot's planned message-aware modules. This is a
        # privileged intent and must also be enabled in the Discord Developer Portal.
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self._persistent_views: list[discord.ui.View] = []
        self.db_pool: asyncpg.Pool | None = None
        self.forms: FormsRepository | None = None

    def register_persistent_view(self, view: discord.ui.View) -> None:
        """Queue a timeout-free view for registration after extensions load.

        Future button modules can call this during setup. The actual registration
        uses Client.add_view so custom buttons survive bot restarts.
        """
        if view.timeout is not None:
            raise ValueError("Persistent views must use timeout=None.")
        self._persistent_views.append(view)

    async def setup_hook(self) -> None:
        await super().setup_hook()
        self.db_pool = await asyncpg.create_pool(
            dsn=self.settings.database_url,
            min_size=1,
            max_size=5,
        )
        self.forms = FormsRepository(self.db_pool)

        await self._remove_legacy_embed_command()

        for extension in self.EXTENSIONS:
            await self.load_extension(extension)
            logger.info("Loaded extension: %s", extension)

        for view in self._persistent_views:
            self.add_view(view)

        await self._restore_persistent_form_buttons()

        if self.settings.guild_id is not None:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(
                "Synchronized %d application command(s) to configured server.",
                len(synced),
            )
            return

        synced = await self.tree.sync()
        logger.info("Synchronized %d global application command(s).", len(synced))

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
            self.forms = None

