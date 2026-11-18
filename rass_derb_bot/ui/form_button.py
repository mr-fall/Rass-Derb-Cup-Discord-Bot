"""Persistent button view for opening a form modal."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from rass_derb_bot.ui.form_submission import FormSubmissionModal

if TYPE_CHECKING:
    from rass_derb_bot.bot import RassDerbBot

logger = logging.getLogger(__name__)

BUTTON_STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}


class FormSubmitButton(discord.ui.Button["FormButtonView"]):
    def __init__(self, bot: RassDerbBot, record: dict[str, Any]) -> None:
        super().__init__(
            label=record["label"],
            style=BUTTON_STYLES.get(record["style"], discord.ButtonStyle.primary),
            custom_id=record["custom_id"],
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        repository = self.bot.forms
        if repository is None:
            await interaction.response.send_message(
                "Forms are temporarily unavailable. Please try again later.",
                ephemeral=True,
            )
            return

        try:
            button = await repository.get_button_by_custom_id(self.custom_id or "")
            if button is None:
                await interaction.response.send_message(
                    "This form button is no longer active.",
                    ephemeral=True,
                )
                return
            if interaction.guild is None or interaction.guild.id != button["guild_id"]:
                await interaction.response.send_message(
                    "This form can only be used in its original server.",
                    ephemeral=True,
                )
                return

            section = await repository.get_section_by_id(
                int(button["guild_id"]),
                int(button["section_id"]),
            )
            if section is None:
                await interaction.response.send_message(
                    "This form section is no longer active.",
                    ephemeral=True,
                )
                return
            if section["staff_channel_id"] is None:
                await interaction.response.send_message(
                    "This form has not been connected to a staff room yet.",
                    ephemeral=True,
                )
                return

            questions = await repository.list_questions(int(section["id"]))
            if not questions:
                await interaction.response.send_message(
                    "This form does not have any questions yet.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_modal(
                FormSubmissionModal(self.bot, section, questions)
            )
        except Exception:
            logger.exception("Failed to open a form modal.")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "The form could not be opened. Please try again later.",
                    ephemeral=True,
                )


class FormButtonView(discord.ui.View):
    """A timeout-free view restored on every bot startup."""

    def __init__(self, bot: RassDerbBot, record: dict[str, Any]) -> None:
        super().__init__(timeout=None)
        self.add_item(FormSubmitButton(bot, record))

