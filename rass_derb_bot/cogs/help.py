"""Ephemeral guide to the bot's form and embed commands."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Preview the bot's commands and form setup steps.",
    )
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Rass Derb Cup bot commands",
            description=(
                "Create the announcement embed, build a form, connect a private "
                "staff room, and attach the form button."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="1 · Create the announcement",
            value=(
                "`/embed` — send a JSON message or embed.\n"
                "Use `/edit-form` to set the submission embed's hex color and large image."
            ),
            inline=False,
        )
        embed.add_field(
            name="2 · Build the form",
            value=(
                "`/form-section` — create a section.\n"
                "`/form-question` — add a short or paragraph question; up to 5 per section."
            ),
            inline=False,
        )
        embed.add_field(
            name="3 · Route and publish it",
            value=(
                "`/setup-form` — select a private staff channel.\n"
                "`/button-form` — attach a button to an embed message link."
            ),
            inline=False,
        )
        embed.add_field(
            name="4 · Edit and review",
            value=(
                "`/edit-form` — select a section, add/edit/remove questions, "
                "change required/type settings, or remove a section.\n"
                "`/help` — show this guide."
            ),
            inline=False,
        )
        embed.add_field(
            name="Button colors",
            value=(
                "Discord buttons support preset Blue, Grey, Green, or Red styles. "
                "Custom hex color applies to the submission embed."
            ),
            inline=False,
        )
        embed.set_footer(
            text="Admin commands require Manage Server permission."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))

