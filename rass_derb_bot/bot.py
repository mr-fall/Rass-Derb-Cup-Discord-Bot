"""Bot client setup, extension loading, and slash-command synchronization."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from rass_derb_bot.config import Settings

logger = logging.getLogger(__name__)


class RassDerbBot(commands.Bot):
    """Central bot client; feature modules are loaded as extensions."""

    EXTENSIONS = (
        "rass_derb_bot.cogs.embed",
        "rass_derb_bot.cogs.ping",
    )

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        # Enabled to match the bot's planned message-aware modules. This is a
        # privileged intent and must also be enabled in the Discord Developer Portal.
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self._persistent_views: list[discord.ui.View] = []

    def register_persistent_view(self, view: discord.ui.View) -> None:
        """Queue a timeout-free view for registration after extensions load.

        Future button modules can call this during setup. The actual registration
        uses Client.add_view so custom buttons survive bot restarts.
        """
        if view.timeout is not None:
            raise ValueError("Persistent views must use timeout=None.")
        self._persistent_views.append(view)

    async def setup_hook(self) -> None:
        for extension in self.EXTENSIONS:
            await self.load_extension(extension)
            logger.info("Loaded extension: %s", extension)

        for view in self._persistent_views:
            self.add_view(view)

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

