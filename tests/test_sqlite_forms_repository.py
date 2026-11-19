"""Unit tests for SQLiteFormsRepository."""

from __future__ import annotations

import unittest
import aiosqlite

from rass_derb_bot.services.sqlite_forms_repository import SQLiteFormsRepository


class SQLiteFormsRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.conn = await aiosqlite.connect(":memory:")
        self.conn.row_factory = aiosqlite.Row
        self.repo = SQLiteFormsRepository(self.conn)
        await self.repo.init_db()

    async def asyncTearDown(self) -> None:
        await self.repo.close()

    async def test_section_crud(self) -> None:
        section = await self.repo.create_section(123456, "pubg-reg", "PUBG Registration", 999)
        self.assertEqual(section["slug"], "pubg-reg")
        self.assertEqual(section["title"], "PUBG Registration")
        self.assertEqual(section["guild_id"], 123456)

        fetched = await self.repo.get_section_by_slug(123456, "pubg-reg")
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["id"], section["id"])

        updated_title = await self.repo.update_section_title(123456, section["id"], "New Title")
        self.assertTrue(updated_title)

        updated_channel = await self.repo.set_staff_channel(123456, section["id"], 555666)
        self.assertTrue(updated_channel)

        updated_app = await self.repo.update_appearance(123456, section["id"], 0xFF0000, "https://example.com/banner.png")
        self.assertTrue(updated_app)

        sections = await self.repo.list_sections(123456)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["title"], "New Title")
        self.assertEqual(sections[0]["embed_color"], 0xFF0000)

    async def test_question_lifecycle(self) -> None:
        section = await self.repo.create_section(123456, "questions", "Questions", 999)
        q1 = await self.repo.add_question(section["id"], "Team Name?", "short", "e.g. Red Dragons", True)
        self.assertEqual(q1["position"], 1)
        self.assertEqual(q1["prompt"], "Team Name?")

        q2 = await self.repo.add_question(section["id"], "Player List?", "paragraph", None, True)
        self.assertEqual(q2["position"], 2)

        questions = await self.repo.list_questions(section["id"])
        self.assertEqual(len(questions), 2)

        updated = await self.repo.update_question(section["id"], q1["id"], "Squad Name?", "short", None, False)
        self.assertTrue(updated)

        deleted = await self.repo.delete_question(section["id"], q1["id"])
        self.assertTrue(deleted)

        remaining = await self.repo.list_questions(section["id"])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], q2["id"])
        self.assertEqual(remaining[0]["position"], 1)

    async def test_button_lifecycle(self) -> None:
        section = await self.repo.create_section(123456, "btn-test", "Buttons", 999)
        btn = await self.repo.create_button(
            "btn_1",
            "form:btn_1",
            123456,
            section["id"],
            111,
            222,
            "Register",
            "primary",
            999,
        )
        self.assertEqual(btn["id"], "btn_1")
        self.assertEqual(btn["label"], "Register")

        active = await self.repo.list_active_buttons()
        self.assertEqual(len(active), 1)

        by_custom = await self.repo.get_button_by_custom_id("form:btn_1")
        self.assertIsNotNone(by_custom)

        archived = await self.repo.archive_section(123456, section["id"])
        self.assertTrue(archived)

        active_after = await self.repo.list_active_buttons()
        self.assertEqual(len(active_after), 0)
