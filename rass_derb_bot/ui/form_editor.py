"""Ephemeral interactive editor for form questions and submission appearance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from rass_derb_bot.ui.form_modals import (
    AddQuestionModal,
    AppearanceModal,
    EditQuestionModal,
    EditSectionTitleModal,
    ConfirmArchiveSectionView,
    ConfirmDeleteQuestionView,
)

if TYPE_CHECKING:
    from rass_derb_bot.bot import RassDerbBot


class FormEditorView(discord.ui.View):
    def __init__(
        self,
        bot: RassDerbBot,
        guild_id: int,
        sections: list[dict[str, Any]],
    ) -> None:
        super().__init__(timeout=600)
        self.bot = bot
        self.guild_id = guild_id
        self.sections = sections[:25]
        self.section = self.sections[0] if self.sections else None
        self.questions: list[dict[str, Any]] = []
        self.selected_question_id: int | None = None
        self.editor_message: discord.WebhookMessage | None = None

    async def load(self) -> None:
        if self.section is not None and self.bot.forms is not None:
            self.questions = await self.bot.forms.list_questions(int(self.section["id"]))
        self._build_components()

    def _build_components(self) -> None:
        self.clear_items()
        if not self.sections:
            return

        self.add_item(SectionSelect(self))
        if self.questions:
            self.add_item(QuestionSelect(self))

        selected = self.selected_question_id is not None
        self.add_item(AddQuestionButton(self, "short"))
        self.add_item(AddQuestionButton(self, "paragraph"))
        self.add_item(EditQuestionButton(self, disabled=not selected))
        self.add_item(RemoveQuestionButton(self, disabled=not selected))
        self.add_item(ToggleQuestionStyleButton(self, disabled=not selected))
        self.add_item(ToggleRequiredButton(self, disabled=not selected))
        self.add_item(AppearanceButton(self))
        self.add_item(EditSectionTitleButton(self))
        self.add_item(ArchiveSectionButton(self))

    def render_embed(self) -> discord.Embed:
        if self.section is None:
            return discord.Embed(
                title="Form editor",
                description="There are no active sections in this server yet.",
                color=discord.Color.blurple(),
            )

        section = self.section
        color_value = int(section["embed_color"])
        staff_channel_id = section["staff_channel_id"]
        staff_room = (
            f"<#{staff_channel_id}>" if staff_channel_id is not None else "Not configured"
        )
        image_description = (
            "Custom image URL configured."
            if section["image_url"]
            else "The saved Rass Derb banner will be attached to submissions."
        )
        embed = discord.Embed(
            title=f"Edit form · {section['title']}"[:256],
            description=(
                f"Section: `{section['slug']}`\n"
                f"Staff room: {staff_room}\n"
                f"Embed color: `#{color_value:06X}`\n"
                f"{image_description}"
            ),
            color=discord.Color(color_value),
        )
        if section["image_url"]:
            embed.set_image(url=section["image_url"])

        if not self.questions:
            embed.add_field(
                name="Questions",
                value="No questions yet. Add one below or use `/form-question`.",
                inline=False,
            )
        else:
            for position, question in enumerate(self.questions, start=1):
                required = "Required" if question["required"] else "Optional"
                style = "Paragraph" if question["input_style"] == "paragraph" else "Short"
                embed.add_field(
                    name=f"{position}. {question['prompt']}"[:256],
                    value=f"{style} · {required}",
                    inline=False,
                )
        return embed

    async def reload(self, *, update_message: bool = True) -> None:
        if self.bot.forms is None:
            return

        self.sections = (await self.bot.forms.list_sections(self.guild_id))[:25]
        current_id = int(self.section["id"]) if self.section is not None else None
        self.section = next(
            (item for item in self.sections if int(item["id"]) == current_id),
            self.sections[0] if self.sections else None,
        )
        self.questions = (
            await self.bot.forms.list_questions(int(self.section["id"]))
            if self.section is not None
            else []
        )
        valid_ids = {int(question["id"]) for question in self.questions}
        if self.selected_question_id not in valid_ids:
            self.selected_question_id = None
        self._build_components()
        if update_message and self.editor_message is not None:
            await self.editor_message.edit(
                embed=self.render_embed(),
                view=self if self.sections else None,
            )

    async def select_section(
        self,
        interaction: discord.Interaction,
        section_id: int,
    ) -> None:
        if self.bot.forms is None:
            await interaction.response.send_message(
                "The form database is unavailable.",
                ephemeral=True,
            )
            return
        self.section = await self.bot.forms.get_section_by_id(
            self.guild_id,
            section_id,
        )
        if self.section is None:
            await interaction.response.send_message(
                "That section is no longer active.",
                ephemeral=True,
            )
            return
        self.questions = await self.bot.forms.list_questions(section_id)
        self.selected_question_id = None
        self._build_components()
        await interaction.response.edit_message(embed=self.render_embed(), view=self)

    async def select_question(
        self,
        interaction: discord.Interaction,
        question_id: int,
    ) -> None:
        self.selected_question_id = question_id
        self._build_components()
        await interaction.response.edit_message(embed=self.render_embed(), view=self)


class SectionSelect(discord.ui.Select):
    def __init__(self, editor: FormEditorView) -> None:
        selected_id = int(editor.section["id"]) if editor.section else None
        options = [
            discord.SelectOption(
                label=str(section["title"])[:100],
                value=str(section["id"]),
                description=f"/{section['slug']}"[:100],
                default=int(section["id"]) == selected_id,
            )
            for section in editor.sections
        ]
        super().__init__(
            placeholder="Choose a form section",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.editor.select_section(interaction, int(self.values[0]))


class QuestionSelect(discord.ui.Select):
    def __init__(self, editor: FormEditorView) -> None:
        options = [
            discord.SelectOption(
                label=str(question["prompt"])[:100],
                value=str(question["id"]),
                description=(
                    f"{question['input_style']} · "
                    f"{'required' if question['required'] else 'optional'}"
                )[:100],
                default=int(question["id"]) == editor.selected_question_id,
            )
            for question in editor.questions[:25]
        ]
        super().__init__(
            placeholder="Choose a question to edit or remove",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.editor.select_question(interaction, int(self.values[0]))


class AddQuestionButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView, style: str) -> None:
        label = "Add short question" if style == "short" else "Add paragraph question"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success,
            row=2,
        )
        self.editor = editor
        self.input_style = style

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.editor.section is None:
            await interaction.response.send_message(
                "Choose or create a section first.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            AddQuestionModal(self.editor, self.input_style)
        )


class EditQuestionButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView, *, disabled: bool) -> None:
        super().__init__(
            label="Edit selected",
            style=discord.ButtonStyle.primary,
            disabled=disabled,
            row=2,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.editor.section is None or self.editor.selected_question_id is None:
            await interaction.response.send_message(
                "Select a question to edit.",
                ephemeral=True,
            )
            return
        question = await self.editor.bot.forms.get_question(
            int(self.editor.section["id"]),
            self.editor.selected_question_id,
        )
        if question is None:
            await interaction.response.send_message(
                "That question no longer exists.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            EditQuestionModal(self.editor, question)
        )


class RemoveQuestionButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView, *, disabled: bool) -> None:
        super().__init__(
            label="Remove selected",
            style=discord.ButtonStyle.danger,
            disabled=disabled,
            row=2,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.editor.section is None or self.editor.selected_question_id is None:
            await interaction.response.send_message(
                "Select a question to remove.",
                ephemeral=True,
            )
            return
        question = await self.editor.bot.forms.get_question(
            int(self.editor.section["id"]),
            self.editor.selected_question_id,
        )
        if question is None:
            await interaction.response.send_message(
                "That question no longer exists.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Remove “{question['prompt']}” from this form?",
            view=ConfirmDeleteQuestionView(self.editor, question),
            ephemeral=True,
        )


class AppearanceButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView) -> None:
        super().__init__(
            label="Edit embed appearance",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.editor.section is None:
            await interaction.response.send_message(
                "Choose a form section first.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(AppearanceModal(self.editor))


class EditSectionTitleButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView) -> None:
        super().__init__(
            label="Rename section",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.editor.section is None:
            await interaction.response.send_message(
                "Choose a form section first.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(EditSectionTitleModal(self.editor))


class ToggleQuestionStyleButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView, *, disabled: bool) -> None:
        super().__init__(
            label="Toggle short / paragraph",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            row=3,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        section = self.editor.section
        question_id = self.editor.selected_question_id
        repository = self.editor.bot.forms
        if section is None or question_id is None or repository is None:
            await interaction.response.send_message(
                "Select a question first.",
                ephemeral=True,
            )
            return
        question = await repository.get_question(int(section["id"]), question_id)
        if question is None:
            await interaction.response.send_message(
                "That question no longer exists.",
                ephemeral=True,
            )
            return
        new_style = (
            "paragraph" if question["input_style"] == "short" else "short"
        )
        await repository.update_question(
            int(section["id"]),
            question_id,
            str(question["prompt"]),
            new_style,
            question["placeholder"],
            bool(question["required"]),
        )
        await self.editor.reload(update_message=False)
        await interaction.response.edit_message(
            embed=self.editor.render_embed(),
            view=self.editor,
        )


class ToggleRequiredButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView, *, disabled: bool) -> None:
        super().__init__(
            label="Toggle required / optional",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            row=3,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        section = self.editor.section
        question_id = self.editor.selected_question_id
        repository = self.editor.bot.forms
        if section is None or question_id is None or repository is None:
            await interaction.response.send_message(
                "Select a question first.",
                ephemeral=True,
            )
            return
        question = await repository.get_question(int(section["id"]), question_id)
        if question is None:
            await interaction.response.send_message(
                "That question no longer exists.",
                ephemeral=True,
            )
            return
        required = not bool(question["required"])
        await repository.update_question(
            int(section["id"]),
            question_id,
            str(question["prompt"]),
            str(question["input_style"]),
            question["placeholder"],
            required,
        )
        await self.editor.reload(update_message=False)
        await interaction.response.edit_message(
            embed=self.editor.render_embed(),
            view=self.editor,
        )


class ArchiveSectionButton(discord.ui.Button):
    def __init__(self, editor: FormEditorView) -> None:
        super().__init__(
            label="Remove section",
            style=discord.ButtonStyle.danger,
            row=3,
        )
        self.editor = editor

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.editor.section is None:
            await interaction.response.send_message(
                "Choose a form section first.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Remove the “{self.editor.section['title']}” section and disable its form buttons?",
            view=ConfirmArchiveSectionView(self.editor),
            ephemeral=True,
        )
