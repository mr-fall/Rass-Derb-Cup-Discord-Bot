"""SQLite persistent storage for form sections, questions, and message buttons."""

from __future__ import annotations

from typing import Any
import aiosqlite


class SQLiteFormsRepository:
    """Async repository using a local SQLite database with full parity to PostgreSQL."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def init_db(self) -> None:
        """Create required tables and indexes if they do not exist."""
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS discord_form_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                slug TEXT NOT NULL,
                title TEXT NOT NULL,
                staff_channel_id INTEGER,
                embed_color INTEGER NOT NULL DEFAULT 3049182,
                image_url TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS discord_form_sections_guild_slug_unique 
                ON discord_form_sections (guild_id, slug);

            CREATE INDEX IF NOT EXISTS discord_form_sections_guild_active_idx 
                ON discord_form_sections (guild_id, active);

            CREATE TABLE IF NOT EXISTS discord_form_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER NOT NULL REFERENCES discord_form_sections(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                input_style TEXT NOT NULL DEFAULT 'short',
                placeholder TEXT,
                required INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS discord_form_questions_section_position_idx 
                ON discord_form_questions (section_id, position);

            CREATE TABLE IF NOT EXISTS discord_form_buttons (
                id TEXT PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                section_id INTEGER NOT NULL REFERENCES discord_form_sections(id) ON DELETE CASCADE,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                style TEXT NOT NULL DEFAULT 'primary',
                custom_id TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS discord_form_buttons_message_unique 
                ON discord_form_buttons (message_id);

            CREATE INDEX IF NOT EXISTS discord_form_buttons_guild_active_idx 
                ON discord_form_buttons (guild_id, active);
            """
        )
        await self.db.commit()

    async def create_section(
        self,
        guild_id: int,
        slug: str,
        title: str,
        created_by: int,
    ) -> dict[str, Any]:
        cursor = await self.db.execute(
            """
            INSERT INTO discord_form_sections (guild_id, slug, title, created_by)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, slug, title, created_by),
        )
        await self.db.commit()
        section_id = cursor.lastrowid
        section = await self.get_section_by_id(guild_id, section_id, active_only=False)
        assert section is not None
        return section

    async def list_sections(self, guild_id: int) -> list[dict[str, Any]]:
        async with self.db.execute(
            """
            SELECT *
            FROM discord_form_sections
            WHERE guild_id = ? AND active = 1
            ORDER BY title, id
            """,
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_section_by_slug(
        self,
        guild_id: int,
        slug: str,
        *,
        active_only: bool = True,
    ) -> dict[str, Any] | None:
        sql = "SELECT * FROM discord_form_sections WHERE guild_id = ? AND slug = ?"
        params: list[Any] = [guild_id, slug]
        if active_only:
            sql += " AND active = 1"
        async with self.db.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_section_by_id(
        self,
        guild_id: int,
        section_id: int,
        *,
        active_only: bool = True,
    ) -> dict[str, Any] | None:
        sql = "SELECT * FROM discord_form_sections WHERE guild_id = ? AND id = ?"
        params: list[Any] = [guild_id, section_id]
        if active_only:
            sql += " AND active = 1"
        async with self.db.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_section_title(
        self,
        guild_id: int,
        section_id: int,
        title: str,
    ) -> bool:
        cursor = await self.db.execute(
            """
            UPDATE discord_form_sections
            SET title = ?
            WHERE guild_id = ? AND id = ? AND active = 1
            """,
            (title, guild_id, section_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def set_staff_channel(
        self,
        guild_id: int,
        section_id: int,
        channel_id: int,
    ) -> bool:
        cursor = await self.db.execute(
            """
            UPDATE discord_form_sections
            SET staff_channel_id = ?
            WHERE guild_id = ? AND id = ? AND active = 1
            """,
            (channel_id, guild_id, section_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def update_appearance(
        self,
        guild_id: int,
        section_id: int,
        color: int,
        image_url: str | None,
    ) -> bool:
        cursor = await self.db.execute(
            """
            UPDATE discord_form_sections
            SET embed_color = ?, image_url = ?
            WHERE guild_id = ? AND id = ? AND active = 1
            """,
            (color, image_url, guild_id, section_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def list_questions(self, section_id: int) -> list[dict[str, Any]]:
        async with self.db.execute(
            """
            SELECT *
            FROM discord_form_questions
            WHERE section_id = ?
            ORDER BY position, id
            """,
            (section_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_question(
        self,
        section_id: int,
        question_id: int,
    ) -> dict[str, Any] | None:
        async with self.db.execute(
            """
            SELECT *
            FROM discord_form_questions
            WHERE section_id = ? AND id = ?
            """,
            (section_id, question_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_question(
        self,
        section_id: int,
        prompt: str,
        input_style: str,
        placeholder: str | None,
        required: bool,
    ) -> dict[str, Any]:
        async with self.db.execute(
            "SELECT id FROM discord_form_sections WHERE id = ? AND active = 1",
            (section_id,),
        ) as cursor:
            if await cursor.fetchone() is None:
                raise LookupError("Form section no longer exists.")

        async with self.db.execute(
            "SELECT COUNT(*) FROM discord_form_questions WHERE section_id = ?",
            (section_id,),
        ) as cursor:
            count_row = await cursor.fetchone()
            question_count = count_row[0] if count_row else 0
            if question_count >= 5:
                raise ValueError("Discord forms support up to 5 questions per section.")

        position = int(question_count) + 1
        cursor = await self.db.execute(
            """
            INSERT INTO discord_form_questions
                (section_id, position, prompt, input_style, placeholder, required)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                section_id,
                position,
                prompt,
                input_style,
                placeholder,
                1 if required else 0,
            ),
        )
        await self.db.commit()
        question_id = cursor.lastrowid
        question = await self.get_question(section_id, question_id)
        assert question is not None
        return question

    async def update_question(
        self,
        section_id: int,
        question_id: int,
        prompt: str,
        input_style: str,
        placeholder: str | None,
        required: bool,
    ) -> bool:
        cursor = await self.db.execute(
            """
            UPDATE discord_form_questions
            SET prompt = ?, input_style = ?, placeholder = ?, required = ?
            WHERE section_id = ? AND id = ?
            """,
            (
                prompt,
                input_style,
                placeholder,
                1 if required else 0,
                section_id,
                question_id,
            ),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def delete_question(self, section_id: int, question_id: int) -> bool:
        async with self.db.execute(
            "SELECT position FROM discord_form_questions WHERE section_id = ? AND id = ?",
            (section_id, question_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return False
            pos = row[0]

        await self.db.execute(
            "DELETE FROM discord_form_questions WHERE section_id = ? AND id = ?",
            (section_id, question_id),
        )
        await self.db.execute(
            "UPDATE discord_form_questions SET position = position - 1 WHERE section_id = ? AND position > ?",
            (section_id, pos),
        )
        await self.db.commit()
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
        await self.db.execute(
            """
            INSERT INTO discord_form_buttons
                (id, custom_id, guild_id, section_id, channel_id, message_id, label, style, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                button_id,
                custom_id,
                guild_id,
                section_id,
                channel_id,
                message_id,
                label,
                style,
                created_by,
            ),
        )
        await self.db.commit()
        async with self.db.execute(
            "SELECT * FROM discord_form_buttons WHERE id = ?", (button_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            return dict(row)

    async def delete_button(self, button_id: str) -> None:
        await self.db.execute(
            "DELETE FROM discord_form_buttons WHERE id = ?", (button_id,)
        )
        await self.db.commit()

    async def get_button_by_custom_id(
        self,
        custom_id: str,
    ) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM discord_form_buttons WHERE custom_id = ? AND active = 1",
            (custom_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_active_buttons(self) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM discord_form_buttons WHERE active = 1 ORDER BY created_at, id"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def list_section_buttons(self, section_id: int) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM discord_form_buttons WHERE section_id = ? AND active = 1 ORDER BY created_at",
            (section_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def archive_section(self, guild_id: int, section_id: int) -> bool:
        cursor = await self.db.execute(
            "UPDATE discord_form_sections SET active = 0 WHERE guild_id = ? AND id = ? AND active = 1",
            (guild_id, section_id),
        )
        if cursor.rowcount == 0:
            return False
        await self.db.execute(
            "UPDATE discord_form_buttons SET active = 0 WHERE section_id = ?",
            (section_id,),
        )
        await self.db.commit()
        return True

    async def close(self) -> None:
        await self.db.close()
