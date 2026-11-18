"""Respond to direct bot mentions with its current gateway latency."""

from __future__ import annotations

import discord
from discord.ext import commands

from rass_derb_bot.services.ping import format_ping


class MentionPingCog(commands.Cog):
    """Reply with the bot's WebSocket heartbeat latency when mentioned."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.bot.user is None:
            return
        if self.bot.user not in message.mentions:
            return

        await message.reply(
            format_ping(self.bot.latency),
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MentionPingCog(bot))

