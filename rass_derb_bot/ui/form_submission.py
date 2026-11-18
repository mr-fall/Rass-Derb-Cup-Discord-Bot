"""Dynamic modal and private staff-room delivery for form submissions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from rass_derb_bot.bot import RassDerbBot

logger = logging.getLogger(__name__)
DEFAULT_BANNER = Path(__file__).resolve().parents[1] / "assets" / "form-banner.png"


class FormSubmissionModal(discord.ui.Modal):
    def __init__(
        self,
        bot: RassDerbBot,
        section: dict[str, Any],
        questions: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            title=str(section["title"])[:45],
            custom_id=f"form:submit:{section['id']}:{uuid.uuid4().hex}",
            timeout=300,
        )
        self.bot = bot
        self.section = section
        self.questions = questions[:5]
        self.answer_inputs: list[tuple[dict[str, Any], discord.ui.TextInput]] = []

        for question in self.questions:
            text_input = discord.ui.TextInput(
                label=str(question["prompt"])[:45],
                style=(
                    discord.TextStyle.paragraph
                    if question["input_style"] == "paragraph"
                    else discord.TextStyle.short
                ),
                placeholder=question["placeholder"] or None,
                required=bool(question["required"]),
                max_length=1000,
            )
            self.answer_inputs.append((question, text_input))
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None or guild.id != self.section["guild_id"]:
            await interaction.response.send_message(
                "This form can only be submitted in its original server.",
                ephemeral=True,
            )
            return

        channel_id = self.section["staff_channel_id"]
        if channel_id is None:
            await interaction.response.send_message(
                "The staff room for this form has not been configured.",
                ephemeral=True,
            )
            return

        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except discord.HTTPException:
                channel = None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "The configured staff room is unavailable. Please contact a server admin.",
                ephemeral=True,
            )
            return

        user = interaction.user
        avatar_url = user.display_avatar.url
        embed = discord.Embed(
            title=f"New submission · {self.section['title']}"[:256],
            color=discord.Color(int(self.section["embed_color"])),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(name=user.display_name, icon_url=avatar_url)
        embed.set_thumbnail(url=avatar_url)
        embed.add_field(
            name="Member",
            value=f"{user.mention}\n`{user.id}`",
            inline=False,
        )

        for question, text_input in self.answer_inputs:
            answer = text_input.value.strip() or "No answer provided."
            embed.add_field(
                name=str(question["prompt"])[:256],
                value=answer[:1024],
                inline=False,
            )

        image_url = self.section["image_url"]
        file: discord.File | None = None
        if image_url:
            embed.set_image(url=image_url)
        elif DEFAULT_BANNER.is_file():
            file = discord.File(DEFAULT_BANNER, filename="form-banner.png")
            embed.set_image(url="attachment://form-banner.png")

        embed.set_footer(text="Rass Derb Cup · Private form submission")
        try:
            send_options: dict[str, Any] = {
                "embed": embed,
                "allowed_mentions": discord.AllowedMentions.none(),
            }
            if file is not None:
                send_options["file"] = file
            await channel.send(**send_options)
        except discord.Forbidden:
            await interaction.response.send_message(
                "The staff room is private to the bot. Ask an admin to grant it "
                "View Channel, Send Messages, and Embed Links.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            logger.exception("Failed to deliver a form submission to the staff room.")
            await interaction.response.send_message(
                "Your submission could not be delivered. Please try again or contact staff.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Your question was sent privately to the staff team.",
            ephemeral=True,
        )

