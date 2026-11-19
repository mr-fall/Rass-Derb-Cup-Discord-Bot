"""Unit tests for ping command and mention formatting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from rass_derb_bot.cogs.ping import MentionPingCog
from rass_derb_bot.services.ping import format_ping


class FormatPingTests(unittest.TestCase):
    def test_formats_latency_in_milliseconds(self) -> None:
        self.assertEqual(format_ping(0.042), "Pong — 42 ms")

    def test_never_displays_negative_latency(self) -> None:
        self.assertEqual(format_ping(-0.1), "Pong — 0 ms")


class MentionPingListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_replies_latency_when_ping_requested(self) -> None:
        bot_user = object()
        bot = SimpleNamespace(user=bot_user, latency=0.042)
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False, id=111222),
            content="@bot ping",
            mentions=[bot_user],
            reply=AsyncMock(),
        )

        await MentionPingCog(bot).on_message(message)

        message.reply.assert_awaited_once()
        self.assertEqual(message.reply.await_args.args[0], "Pong — 42 ms")

    async def test_replies_professional_message_on_general_mention(self) -> None:
        bot_user = object()
        bot = SimpleNamespace(user=bot_user, latency=0.042)
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False, id=922592319826427955),
            content="@bot salam",
            mentions=[bot_user],
            reply=AsyncMock(),
        )

        await MentionPingCog(bot).on_message(message)

        message.reply.assert_awaited_once()
        self.assertIn("/help", message.reply.await_args.args[0])

    async def test_ignores_messages_from_bots(self) -> None:
        bot_user = object()
        bot = SimpleNamespace(user=bot_user, latency=0.042)
        message = SimpleNamespace(
            author=SimpleNamespace(bot=True, id=999),
            content="@bot hello",
            mentions=[bot_user],
            reply=AsyncMock(),
        )

        await MentionPingCog(bot).on_message(message)

        message.reply.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
