"""Admin command for sending custom tournament JSON embeds."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from rass_derb_bot.services.embed_payload import (
    EmbedPayloadError,
    parse_embed_payload,
)

logger = logging.getLogger(__name__)


def is_staff(user: discord.Member) -> bool:
    """Check if the user is the bot owner or has management permissions."""
    if user.id == 922592319826427955:
        return True
    perms = user.guild_permissions
    return (
        perms.administrator
        or perms.manage_guild
        or perms.manage_channels
        or perms.manage_messages
    )


class EmbedCog(commands.Cog):
    """Slash commands for composing and sending Discord embeds."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="embed",
        description="Send a custom JSON embed or announcement to a text channel.",
    )
    @app_commands.describe(
        payload="JSON with content, embeds, or top-level embed fields.",
        channel="Where to post; defaults to this channel.",
    )
    async def embed(
        self,
        interaction: discord.Interaction,
        payload: app_commands.Range[str, 1, 4000],
        channel: discord.TextChannel | None = None,
    ) -> None:
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ You need staff permissions (Administrator or Manage Channels/Messages/Server) to use this command.",
                ephemeral=True,
            )
            return

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Choose a text channel where I can post.",
                ephemeral=True,
            )
            return

        try:
            message_content, embeds = parse_embed_payload(payload)
        except EmbedPayloadError as error:
            await interaction.response.send_message(
                f"Invalid embed JSON: {error}",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            message = await target.send(
                content=message_content,
                embeds=embeds,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"I can't post in {target.mention}. Check my View Channel, "
                "Send Messages, and Embed Links permissions.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            logger.exception("Discord rejected an embed send request.")
            await interaction.followup.send(
                "Discord couldn't send that payload. Check its embed limits and "
                "the bot's channel permissions, then try again.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Posted your message in {target.mention}: {message.jump_url}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmbedCog(bot))
