"""Persistent storage for form sections, questions, and message buttons."""

from __future__ import annotations

from typing import Any

import asyncpg


class FormsRepository:
    """Small asyncpg repository over the shared PostgreSQL database."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def init_db(self) -> None:
        """Create required tables and indexes if they do not exist."""
        await self.pool.execute(
            """
            CREATE TABLE IF NOT EXISTS discord_form_sections (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                slug VARCHAR(50) NOT NULL,
                title VARCHAR(100) NOT NULL,
                staff_channel_id BIGINT,
                embed_color INTEGER NOT NULL DEFAULT 3049182,
                image_url TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_by BIGINT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );

            CREATE UNIQUE INDEX IF NOT EXISTS discord_form_sections_guild_slug_unique 
                ON discord_form_sections (guild_id, slug);

            CREATE INDEX IF NOT EXISTS discord_form_sections_guild_active_idx 
                ON discord_form_sections (guild_id, active);

            CREATE TABLE IF NOT EXISTS discord_form_questions (
                id SERIAL PRIMARY KEY,
                section_id INTEGER NOT NULL REFERENCES discord_form_sections(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                prompt VARCHAR(45) NOT NULL,
                input_style VARCHAR(12) NOT NULL DEFAULT 'short',
                placeholder VARCHAR(100),
                required BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS discord_form_questions_section_position_idx 
                ON discord_form_questions (section_id, position);

            CREATE TABLE IF NOT EXISTS discord_form_buttons (
                id VARCHAR(36) PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                section_id INTEGER NOT NULL REFERENCES discord_form_sections(id) ON DELETE CASCADE,
                channel_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                label VARCHAR(80) NOT NULL,
                style VARCHAR(12) NOT NULL DEFAULT 'primary',
                custom_id VARCHAR(100) NOT NULL UNIQUE,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_by BIGINT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );

            CREATE UNIQUE INDEX IF NOT EXISTS discord_form_buttons_message_unique 
                ON discord_form_buttons (message_id);

            CREATE INDEX IF NOT EXISTS discord_form_buttons_guild_active_idx 
                ON discord_form_buttons (guild_id, active);
            """
        )

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
        clean = slug.strip()
        if "(/" in clean and clean.endswith(")"):
            clean = clean.split("(/")[-1].rstrip(")")
        clean = clean.lstrip("/")

        sec_id = int(clean) if clean.isdigit() else -1
        row = await self.pool.fetchrow(
            """
            SELECT *
            FROM discord_form_sections
            WHERE guild_id = $1
              AND (
                  LOWER(slug) = LOWER($2)
                  OR LOWER(title) = LOWER($2)
                  OR slug = $2
                  OR id = $4
              )
              AND ($3::boolean = FALSE OR active = TRUE)
            ORDER BY id
            LIMIT 1
            """,
            guild_id,
            clean,
            active_only,
            sec_id,
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
