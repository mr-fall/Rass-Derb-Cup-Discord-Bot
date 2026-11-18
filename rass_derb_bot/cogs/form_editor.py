"""Slash-command entry point for the interactive form editor."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from rass_derb_bot.ui.form_editor import FormEditorView


class FormEditorCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="edit-form",
        description="Select a section to edit questions and embed appearance.",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def edit_form(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "Use this command inside a server.",
                ephemeral=True,
            )
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server permission to edit forms.",
                ephemeral=True,
            )
            return
        if self.bot.forms is None:
            await interaction.response.send_message(
                "The form database is unavailable.",
                ephemeral=True,
            )
            return

        sections = await self.bot.forms.list_sections(interaction.guild.id)
        if not sections:
            await interaction.response.send_message(
                "There are no form sections yet. Start with `/form-section`.",
                ephemeral=True,
            )
            return

        view = FormEditorView(self.bot, interaction.guild.id, sections)
        await view.load()
        await interaction.response.send_message(
            embed=view.render_embed(),
            view=view,
            ephemeral=True,
        )
        view.editor_message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FormEditorCog(bot))

