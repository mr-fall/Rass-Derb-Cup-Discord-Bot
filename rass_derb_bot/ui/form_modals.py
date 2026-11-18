"""Question and appearance modals plus destructive-action confirmations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import discord

from rass_derb_bot.services.form_utils import FormInputError, parse_color, validate_image_url

if TYPE_CHECKING:
    from rass_derb_bot.ui.form_editor import FormEditorView

logger = logging.getLogger(__name__)


class AddQuestionModal(discord.ui.Modal):
    def __init__(self, editor: FormEditorView, input_style: str) -> None:
        super().__init__(
            title="Add form question",
            timeout=300,
        )
        self.editor = editor
        self.input_style = input_style
        self.prompt = discord.ui.TextInput(
            label="Question (up to 45 characters)",
            max_length=45,
            placeholder="What would you like to ask?",
        )
        self.placeholder = discord.ui.TextInput(
            label="Answer hint (optional)",
            required=False,
            max_length=100,
            placeholder="A short hint shown in the form",
        )
        self.add_item(self.prompt)
        self.add_item(self.placeholder)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        section = self.editor.section
        repository = self.editor.bot.forms
        if section is None or repository is None:
            await interaction.response.send_message(
                "The selected section is no longer available.",
                ephemeral=True,
            )
            return

        try:
            await repository.add_question(
                int(section["id"]),
                self.prompt.value.strip(),
                self.input_style,
                self.placeholder.value.strip() or None,
                True,
            )
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        except Exception:
            logger.exception("Failed to add a form question from the editor.")
            await interaction.response.send_message(
                "The question could not be added. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Question added. Use `/edit-form` to change its settings.",
            ephemeral=True,
        )
        await self.editor.reload()


class EditQuestionModal(discord.ui.Modal):
    def __init__(
        self,
        editor: FormEditorView,
        question: dict[str, Any],
    ) -> None:
        super().__init__(
            title="Edit form question",
            timeout=300,
        )
        self.editor = editor
        self.question = question
        self.prompt = discord.ui.TextInput(
            label="Question (up to 45 characters)",
            default=str(question["prompt"]),
            max_length=45,
        )
        self.placeholder = discord.ui.TextInput(
            label="Answer hint (optional)",
            default=str(question["placeholder"] or ""),
            required=False,
            max_length=100,
        )
        self.add_item(self.prompt)
        self.add_item(self.placeholder)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        section = self.editor.section
        repository = self.editor.bot.forms
        if section is None or repository is None:
            await interaction.response.send_message(
                "The selected section is no longer available.",
                ephemeral=True,
            )
            return

        try:
            updated = await repository.update_question(
                int(section["id"]),
                int(self.question["id"]),
                self.prompt.value.strip(),
                str(self.question["input_style"]),
                self.placeholder.value.strip() or None,
                bool(self.question["required"]),
            )
        except Exception:
            logger.exception("Failed to update a form question.")
            await interaction.response.send_message(
                "The question could not be updated. Please try again.",
                ephemeral=True,
            )
            return
        if not updated:
            await interaction.response.send_message(
                "That question was removed before the edit was saved.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Question updated.", ephemeral=True)
        await self.editor.reload()


class EditSectionTitleModal(discord.ui.Modal):
    def __init__(self, editor: FormEditorView) -> None:
        section = editor.section or {}
        super().__init__(title="Rename form section", timeout=300)
        self.editor = editor
        self.title_input = discord.ui.TextInput(
            label="Section title",
            default=str(section.get("title") or ""),
            max_length=100,
        )
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        section = self.editor.section
        repository = self.editor.bot.forms
        title = self.title_input.value.strip()
        if section is None or repository is None or not title:
            await interaction.response.send_message(
                "Enter a section title and try again.",
                ephemeral=True,
            )
            return
        try:
            updated = await repository.update_section_title(
                self.editor.guild_id,
                int(section["id"]),
                title,
            )
        except Exception:
            logger.exception("Failed to rename a form section.")
            await interaction.response.send_message(
                "The section title could not be updated.",
                ephemeral=True,
            )
            return
        if not updated:
            await interaction.response.send_message(
                "That section is no longer active.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message("Section title updated.", ephemeral=True)
        await self.editor.reload()


class AppearanceModal(discord.ui.Modal):
    def __init__(self, editor: FormEditorView) -> None:
        section = editor.section or {}
        color = int(section.get("embed_color") or 0x2E86DE)
        image_url = str(section.get("image_url") or "")
        super().__init__(
            title="Submission embed appearance",
            timeout=300,
        )
        self.editor = editor
        self.color_input = discord.ui.TextInput(
            label="Embed color (#RRGGBB)",
            default=f"#{color:06X}",
            max_length=7,
        )
        self.image_input = discord.ui.TextInput(
            label="Large image URL (blank uses saved banner)",
            default=image_url[:4000],
            required=False,
            max_length=4000,
            style=discord.TextStyle.short,
        )
        self.add_item(self.color_input)
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        section = self.editor.section
        repository = self.editor.bot.forms
        if section is None or repository is None:
            await interaction.response.send_message(
                "The selected section is no longer available.",
                ephemeral=True,
            )
            return

        try:
            color = parse_color(self.color_input.value)
            image_url = validate_image_url(self.image_input.value)
        except FormInputError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        try:
            updated = await repository.update_appearance(
                self.editor.guild_id,
                int(section["id"]),
                color,
                image_url,
            )
        except Exception:
            logger.exception("Failed to update form submission appearance.")
            await interaction.response.send_message(
                "The embed appearance could not be updated. Please try again.",
                ephemeral=True,
            )
            return
        if not updated:
            await interaction.response.send_message(
                "That section is no longer active.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Submission embed appearance updated.",
            ephemeral=True,
        )
        await self.editor.reload()


class ConfirmDeleteQuestionView(discord.ui.View):
    def __init__(
        self,
        editor: FormEditorView,
        question: dict[str, Any],
    ) -> None:
        super().__init__(timeout=60)
        self.editor = editor
        self.question = question

    @discord.ui.button(
        label="Remove question",
        style=discord.ButtonStyle.danger,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        section = self.editor.section
        repository = self.editor.bot.forms
        if section is None or repository is None:
            await interaction.response.edit_message(
                content="The section is no longer available.",
                view=None,
            )
            return
        removed = await repository.delete_question(
            int(section["id"]),
            int(self.question["id"]),
        )
        await interaction.response.edit_message(
            content="Question removed." if removed else "Question was already removed.",
            view=None,
        )
        await self.editor.reload()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.edit_message(
            content="Removal cancelled.",
            view=None,
        )


class ConfirmArchiveSectionView(discord.ui.View):
    def __init__(self, editor: FormEditorView) -> None:
        super().__init__(timeout=60)
        self.editor = editor

    @discord.ui.button(
        label="Remove section",
        style=discord.ButtonStyle.danger,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        section = self.editor.section
        repository = self.editor.bot.forms
        if section is None or repository is None:
            await interaction.response.edit_message(
                content="The section is no longer available.",
                view=None,
            )
            return

        buttons = await repository.list_section_buttons(int(section["id"]))
        for record in buttons:
            try:
                channel = self.editor.bot.get_channel(int(record["channel_id"]))
                if channel is None:
                    channel = await self.editor.bot.fetch_channel(
                        int(record["channel_id"])
                    )
                if isinstance(channel, discord.TextChannel):
                    message = await channel.fetch_message(int(record["message_id"]))
                    await message.edit(view=None)
            except discord.HTTPException:
                logger.warning(
                    "Could not remove an archived form button from message %s.",
                    record["message_id"],
                )

        archived = await repository.archive_section(
            self.editor.guild_id,
            int(section["id"]),
        )
        await interaction.response.edit_message(
            content="Section removed and its form buttons disabled."
            if archived
            else "That section was already removed.",
            view=None,
        )
        await self.editor.reload()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.edit_message(
            content="Section removal cancelled.",
            view=None,
        )

