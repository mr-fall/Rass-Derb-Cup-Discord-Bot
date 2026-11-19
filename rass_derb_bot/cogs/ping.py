"""Latency check and clean mention handling for Rass Derb Cup bot."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from rass_derb_bot.services.ping import format_ping


class MentionPingCog(commands.Cog):
    """Handle latency checks and professional bot information."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot latency and responsiveness.")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Slash command to check bot latency."""
        latency_ms = max(0, round(self.bot.latency * 1000))
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** `{latency_ms} ms`\n**Status:** `Operational` 🟢",
            color=discord.Color.from_rgb(46, 134, 222),
        )
        embed.set_footer(text="Rass Derb Cup • Esports PUBG MOBILE MEA")
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Professional response when the bot is mentioned."""
        if message.author.bot or self.bot.user is None:
            return
        if self.bot.user not in message.mentions:
            return

        content = message.content.lower()
        if "ping" in content:
            await message.reply(format_ping(self.bot.latency), mention_author=False)
            return

        await message.reply(
            "👋 Hello! I am the official bot for **Rass Derb Cup • Esports PUBG MOBILE MEA**.\n"
            "Use `/help` to view all available commands.",
            mention_author=False,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MentionPingCog(bot))
