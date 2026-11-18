"""Persistent storage for form sections, questions, and message buttons."""

from __future__ import annotations

from typing import Any

import asyncpg


class FormsRepository:
    """Small asyncpg repository over the shared PostgreSQL database."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def create_section(
        self,
        guild_id: int,
        slug: str,
        title: str,
        created_by: int,
    ) -> dict[str, Any]:
        row = await self.pool.fetchrow(
            """
            INSERT INTO discord_form_sections (guild_id, slug, title, created_by)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            guild_id,
            slug,
            title,
            created_by,
        )
        return dict(row)

    async def list_sections(self, guild_id: int) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT *
            FROM discord_form_sections
            WHERE guild_id = $1 AND active = TRUE
            ORDER BY title, id
            """,
            guild_id,
        )
        return [dict(row) for row in rows]

    async def get_section_by_slug(
        self,
        guild_id: int,
        slug: str,
        *,
        active_only: bool = True,
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT *
            FROM discord_form_sections
            WHERE guild_id = $1 AND slug = $2
              AND ($3::boolean = FALSE OR active = TRUE)
            """,
            guild_id,
            slug,
            active_only,
        )
        return dict(row) if row else None

    async def get_section_by_id(
        self,
        guild_id: int,
        section_id: int,
        *,
        active_only: bool = True,
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT *
            FROM discord_form_sections
            WHERE guild_id = $1 AND id = $2
              AND ($3::boolean = FALSE OR active = TRUE)
            """,
            guild_id,
            section_id,
            active_only,
        )
        return dict(row) if row else None

    async def update_section_title(
        self,
        guild_id: int,
        section_id: int,
        title: str,
    ) -> bool:
        result = await self.pool.execute(
            """
            UPDATE discord_form_sections
            SET title = $3
            WHERE guild_id = $1 AND id = $2 AND active = TRUE
            """,
            guild_id,
            section_id,
            title,
        )
        return result.endswith(" 1")

    async def set_staff_channel(
        self,
        guild_id: int,
        section_id: int,
        channel_id: int,
    ) -> bool:
        result = await self.pool.execute(
            """
            UPDATE discord_form_sections
            SET staff_channel_id = $3
            WHERE guild_id = $1 AND id = $2 AND active = TRUE
            """,
            guild_id,
            section_id,
            channel_id,
        )
        return result.endswith(" 1")

    async def update_appearance(
        self,
        guild_id: int,
        section_id: int,
        color: int,
        image_url: str | None,
    ) -> bool:
        result = await self.pool.execute(
            """
            UPDATE discord_form_sections
            SET embed_color = $3, image_url = $4
            WHERE guild_id = $1 AND id = $2 AND active = TRUE
            """,
            guild_id,
            section_id,
            color,
            image_url,
        )
        return result.endswith(" 1")

    async def list_questions(self, section_id: int) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT *
            FROM discord_form_questions
            WHERE section_id = $1
            ORDER BY position, id
            """,
            section_id,
        )
        return [dict(row) for row in rows]

    async def get_question(
        self,
        section_id: int,
        question_id: int,
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT *
            FROM discord_form_questions
            WHERE section_id = $1 AND id = $2
            """,
            section_id,
            question_id,
        )
        return dict(row) if row else None

    async def add_question(
        self,
        section_id: int,
        prompt: str,
        input_style: str,
        placeholder: str | None,
        required: bool,
    ) -> dict[str, Any]:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                exists = await connection.fetchval(
                    """
                    SELECT id
                    FROM discord_form_sections
                    WHERE id = $1 AND active = TRUE
                    FOR UPDATE
                    """,
                    section_id,
                )
                if exists is None:
                    raise LookupError("Form section no longer exists.")

                question_count = await connection.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM discord_form_questions
                    WHERE section_id = $1
                    """,
                    section_id,
                )
                if question_count >= 5:
                    raise ValueError(
                        "Discord forms support up to 5 questions per section."
                    )

                position = int(question_count) + 1
                row = await connection.fetchrow(
                    """
                    INSERT INTO discord_form_questions
                        (section_id, position, prompt, input_style, placeholder, required)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                    """,
                    section_id,
                    position,
                    prompt,
                    input_style,
                    placeholder,
                    required,
                )
                return dict(row)

    async def update_question(
        self,
        section_id: int,
        question_id: int,
        prompt: str,
        input_style: str,
        placeholder: str | None,
        required: bool,
    ) -> bool:
        result = await self.pool.execute(
            """
            UPDATE discord_form_questions
            SET prompt = $3, input_style = $4, placeholder = $5, required = $6
            WHERE section_id = $1 AND id = $2
            """,
            section_id,
            question_id,
            prompt,
            input_style,
            placeholder,
            required,
        )
        return result.endswith(" 1")

    async def delete_question(self, section_id: int, question_id: int) -> bool:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    DELETE FROM discord_form_questions
                    WHERE section_id = $1 AND id = $2
                    RETURNING position
                    """,
                    section_id,
                    question_id,
                )
                if row is None:
                    return False
                await connection.execute(
                    """
                    UPDATE discord_form_questions
                    SET position = position - 1
                    WHERE section_id = $1 AND position > $2
                    """,
                    section_id,
                    row["position"],
                )
                return True

    async def create_button(
        self,
        button_id: str,
        custom_id: str,
        guild_id: int,
        section_id: int,
        channel_id: int,
        message_id: int,
        label: str,
        style: str,
        created_by: int,
    ) -> dict[str, Any]:
        row = await self.pool.fetchrow(
            """
            INSERT INTO discord_form_buttons
                (id, custom_id, guild_id, section_id, channel_id, message_id,
                 label, style, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            button_id,
            custom_id,
            guild_id,
            section_id,
            channel_id,
            message_id,
            label,
            style,
            created_by,
        )
        return dict(row)

    async def delete_button(self, button_id: str) -> None:
        await self.pool.execute(
            "DELETE FROM discord_form_buttons WHERE id = $1",
            button_id,
        )

    async def get_button_by_custom_id(
        self,
        custom_id: str,
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT *
            FROM discord_form_buttons
            WHERE custom_id = $1 AND active = TRUE
            """,
            custom_id,
        )
        return dict(row) if row else None

    async def list_active_buttons(self) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT *
            FROM discord_form_buttons
            WHERE active = TRUE
            ORDER BY created_at, id
            """
        )
        return [dict(row) for row in rows]

    async def list_section_buttons(self, section_id: int) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT *
            FROM discord_form_buttons
            WHERE section_id = $1 AND active = TRUE
            ORDER BY created_at
            """,
            section_id,
        )
        return [dict(row) for row in rows]

    async def archive_section(self, guild_id: int, section_id: int) -> bool:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                result = await connection.execute(
                    """
                    UPDATE discord_form_sections
                    SET active = FALSE
                    WHERE guild_id = $1 AND id = $2 AND active = TRUE
                    """,
                    guild_id,
                    section_id,
                )
                if not result.endswith(" 1"):
                    return False
                await connection.execute(
                    """
                    UPDATE discord_form_buttons
                    SET active = FALSE
                    WHERE section_id = $1
                    """,
                    section_id,
                )
                return True
