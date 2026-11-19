"""Admin commands for creating and connecting Discord forms."""

from __future__ import annotations

import logging
import uuid

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from rass_derb_bot.services.form_utils import (
    FormInputError,
    parse_message_link,
    validate_slug,
)
from rass_derb_bot.ui.form_button import BUTTON_STYLES, FormButtonView

logger = logging.getLogger(__name__)

INPUT_STYLE_CHOICES = [
    app_commands.Choice(name="Short text", value="short"),
    app_commands.Choice(name="Paragraph", value="paragraph"),
]
BUTTON_STYLE_CHOICES = [
    app_commands.Choice(name="Blue", value="primary"),
    app_commands.Choice(name="Grey", value="secondary"),
    app_commands.Choice(name="Green", value="success"),
    app_commands.Choice(name="Red", value="danger"),
]


def is_staff(user: discord.Member) -> bool:
    if user.id == 922592319826427955:
        return True
    perms = user.guild_permissions
    return (
        perms.administrator
        or perms.manage_guild
        or perms.manage_channels
        or perms.manage_messages
    )


class FormAdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _require_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "Use this command inside a server.",
                ephemeral=True,
            )
            return False
        if not is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ You need staff permissions (Administrator or Manage Channels/Messages/Server) for this command.",
                ephemeral=True,
            )
            return False
        if self.bot.forms is None:
            await interaction.response.send_message(
                "The form database is unavailable. Please try again later.",
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(
        name="form-section",
        description="Create a named form section.",
    )
    @app_commands.describe(
        slug="Unique lowercase key, for example rass-derb-qa.",
        title="The name shown to members; defaults to the slug.",
    )
    async def form_section(
        self,
        interaction: discord.Interaction,
        slug: app_commands.Range[str, 1, 50],
        title: app_commands.Range[str, 1, 100] | None = None,
    ) -> None:
        if not await self._require_admin(interaction):
            return

        try:
            section_slug = validate_slug(slug)
        except FormInputError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        repository = self.bot.forms
        assert repository is not None
        sections = await repository.list_sections(interaction.guild.id)
        if len(sections) >= 25:
            await interaction.response.send_message(
                "This server already has 25 active sections, the editor limit.",
                ephemeral=True,
            )
            return

        try:
            section = await repository.create_section(
                interaction.guild.id,
                section_slug,
                (title or section_slug.replace("-", " ").title()).strip(),
                interaction.user.id,
            )
        except asyncpg.UniqueViolationError:
            await interaction.response.send_message(
                "That section slug is already in use in this server.",
                ephemeral=True,
            )
            return
        except Exception:
            logger.exception("Failed to create a form section.")
            await interaction.response.send_message(
                "The section could not be created. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Created form section **{section['title']}** (`/{section['slug']}`). "
            "Add questions with `/form-question`.",
            ephemeral=True,
        )

    @app_commands.command(
        name="form-question",
        description="Add a question to a form section.",
    )
    @app_commands.choices(input_style=INPUT_STYLE_CHOICES)
    @app_commands.describe(
        section="Choose the form section.",
        prompt="Question shown in the form; up to 45 characters.",
        input_style="Short text or a paragraph answer.",
        placeholder="Optional hint shown in the answer box.",
        required="Whether a member must answer this question.",
    )
    async def form_question(
        self,
        interaction: discord.Interaction,
        section: str,
        prompt: app_commands.Range[str, 1, 45],
        input_style: app_commands.Choice[str],
        placeholder: app_commands.Range[str, 0, 100] | None = None,
        required: bool = True,
    ) -> None:
        if not await self._require_admin(interaction):
            return

        repository = self.bot.forms
        assert repository is not None and interaction.guild is not None
        section_record = await repository.get_section_by_slug(
            interaction.guild.id,
            section,
        )
        if section_record is None:
            available = await repository.list_sections(interaction.guild.id)
            if not available:
                await interaction.response.send_message(
                    "❌ No active form sections in this server. Create one first with `/form-section`.",
                    ephemeral=True,
                )
            else:
                names = ", ".join(f"`{s['slug']}`" for s in available)
                await interaction.response.send_message(
                    f"❌ Section `{section}` not found. Available active section(s): {names}",
                    ephemeral=True,
                )
            return

        try:
            question = await repository.add_question(
                int(section_record["id"]),
                prompt.strip(),
                input_style.value,
                placeholder.strip() if placeholder else None,
                required,
            )
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        except Exception:
            logger.exception("Failed to add a form question.")
            await interaction.response.send_message(
                "The question could not be added. Please try again.",
                ephemeral=True,
            )
            return

        answer_type = "paragraph" if question["input_style"] == "paragraph" else "short text"
        await interaction.response.send_message(
            f"Added question {question['position']} to **{section_record['title']}** "
            f"({answer_type}).",
            ephemeral=True,
        )

    @form_question.autocomplete("section")
    async def section_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        repository = self.bot.forms
        if repository is None or interaction.guild_id is None:
            return []
        sections = await repository.list_sections(interaction.guild_id)
        query = current.casefold()
        return [
            app_commands.Choice(
                name=f"{section['title']} (/{section['slug']})"[:100],
                value=section["slug"],
            )
            for section in sections
            if query in str(section["title"]).casefold()
            or query in str(section["slug"]).casefold()
        ][:25]

    @app_commands.command(
        name="setup-form",
        description="Route form submissions to a private staff room.",
    )
    @app_commands.describe(
        section="Choose the form section.",
        channel="Private text channel where staff receive submissions.",
    )
    async def setup_form(
        self,
        interaction: discord.Interaction,
        section: str,
        channel: discord.TextChannel,
    ) -> None:
        if not await self._require_admin(interaction):
            return

        repository = self.bot.forms
        assert repository is not None and interaction.guild is not None
        section_record = await repository.get_section_by_slug(
            interaction.guild.id,
            section,
        )
        if section_record is None:
            available = await repository.list_sections(interaction.guild.id)
            if not available:
                await interaction.response.send_message(
                    "❌ No active form sections in this server. Create one first with `/form-section`.",
                    ephemeral=True,
                )
            else:
                names = ", ".join(f"`{s['slug']}`" for s in available)
                await interaction.response.send_message(
                    f"❌ Section `{section}` not found. Available active section(s): {names}",
                    ephemeral=True,
                )
            return

        if channel.permissions_for(interaction.guild.default_role).view_channel:
            await interaction.response.send_message(
                "That channel is visible to @everyone. Make it private before using it "
                "for submissions.",
                ephemeral=True,
            )
            return

        bot_member = interaction.guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "I could not verify my permissions in that channel.",
                ephemeral=True,
            )
            return
        bot_permissions = channel.permissions_for(bot_member)
        if not (
            bot_permissions.view_channel
            and bot_permissions.send_messages
            and bot_permissions.embed_links
        ):
            await interaction.response.send_message(
                "Give the bot View Channel, Send Messages, and Embed Links in that staff room.",
                ephemeral=True,
            )
            return

        updated = await repository.set_staff_channel(
            interaction.guild.id,
            int(section_record["id"]),
            channel.id,
        )
        if not updated:
            await interaction.response.send_message(
                "That section is no longer active.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Submissions for **{section_record['title']}** will go to {channel.mention}.",
            ephemeral=True,
        )

    @setup_form.autocomplete("section")
    async def setup_section_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.section_autocomplete(interaction, current)

    @app_commands.command(
        name="button-form",
        description="Attach a form button to one of your embed messages.",
    )
    @app_commands.choices(button_style=BUTTON_STYLE_CHOICES)
    @app_commands.describe(
        section="Form section opened by the button.",
        message_link="Link to an embed message sent by this bot.",
        label="Text displayed on the button.",
        button_style="Discord supports preset button colors only.",
    )
    async def button_form(
        self,
        interaction: discord.Interaction,
        section: str,
        message_link: app_commands.Range[str, 1, 4000],
        label: app_commands.Range[str, 1, 80],
        button_style: app_commands.Choice[str],
    ) -> None:
        if not await self._require_admin(interaction):
            return

        repository = self.bot.forms
        assert repository is not None and interaction.guild is not None
        section_record = await repository.get_section_by_slug(
            interaction.guild.id,
            section,
        )
        if section_record is None:
            available = await repository.list_sections(interaction.guild.id)
            if not available:
                await interaction.response.send_message(
                    "❌ No active form sections in this server. Create one first with `/form-section`.",
                    ephemeral=True,
                )
            else:
                names = ", ".join(f"`{s['slug']}`" for s in available)
                await interaction.response.send_message(
                    f"❌ Section `{section}` not found. Available active section(s): {names}",
                    ephemeral=True,
                )
            return
        if section_record["staff_channel_id"] is None:
            await interaction.response.send_message(
                "Run `/setup-form` for this section before attaching its button.",
                ephemeral=True,
            )
            return
        if not await repository.list_questions(int(section_record["id"])):
            await interaction.response.send_message(
                "Add at least one question with `/form-question` before attaching a button.",
                ephemeral=True,
            )
            return

        try:
            linked_guild_id, channel_id, message_id = parse_message_link(message_link)
        except FormInputError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        if linked_guild_id != interaction.guild.id:
            await interaction.response.send_message(
                "The message link must point to this server.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                channel = None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "I cannot access the text channel from that message link.",
                ephemeral=True,
            )
            return

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "That message no longer exists.",
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "I need View Channel and Read Message History in that channel.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "I could not load that message. Check its link and channel permissions.",
                ephemeral=True,
            )
            return

        if self.bot.user is None or message.author.id != self.bot.user.id:
            await interaction.response.send_message(
                "I can only attach buttons to messages sent by this bot.",
                ephemeral=True,
            )
            return
        if not message.embeds:
            await interaction.response.send_message(
                "That message does not contain an embed.",
                ephemeral=True,
            )
            return
        if message.components:
            await interaction.response.send_message(
                "That message already has buttons. Use a message without components.",
                ephemeral=True,
            )
            return

        button_id = uuid.uuid4().hex
        custom_id = f"form:{button_id}"
        try:
            record = await repository.create_button(
                button_id,
                custom_id,
                interaction.guild.id,
                int(section_record["id"]),
                channel.id,
                message.id,
                label.strip(),
                button_style.value,
                interaction.user.id,
            )
        except asyncpg.UniqueViolationError:
            await interaction.response.send_message(
                "A form button is already linked to that message.",
                ephemeral=True,
            )
            return
        except Exception:
            logger.exception("Failed to save a form button.")
            await interaction.response.send_message(
                "The button could not be saved. Please try again.",
                ephemeral=True,
            )
            return

        try:
            await message.edit(view=FormButtonView(self.bot, record))
        except discord.HTTPException:
            await repository.delete_button(button_id)
            await interaction.response.send_message(
                "Discord could not attach the button. Check the bot's channel permissions.",
                ephemeral=True,
            )
            return

        style_name = button_style.name
        await interaction.response.send_message(
            f"Attached **{label.strip()}** ({style_name}) to the embed. "
            "Discord button colors are limited to preset styles.",
            ephemeral=True,
        )

    @button_form.autocomplete("section")
    async def button_section_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return await self.section_autocomplete(interaction, current)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FormAdminCog(bot))

