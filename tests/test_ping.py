"""Unit tests for mention-ping response formatting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from rass_derb_bot.cogs.ping import MentionPingCog
from rass_derb_bot.services.ping import format_ping


class FormatPingTests(unittest.TestCase):
    def test_formats_latency_in_milliseconds(self) -> None:
        self.assertEqual(format_ping(0.042), "Pong — 42 ms")

    def test_never_displays_negative_latency(self) -> None:
        self.assertEqual(format_ping(-0.1), "Pong — 0 ms")


class MentionPingListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_replies_when_the_bot_is_mentioned(self) -> None:
        bot_user = object()
        bot = SimpleNamespace(user=bot_user, latency=0.042)
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False),
            mentions=[bot_user],
            reply=AsyncMock(),
        )

        await MentionPingCog(bot).on_message(message)

        message.reply.assert_awaited_once()
        self.assertEqual(message.reply.await_args.args[0], "Pong — 42 ms")
        self.assertFalse(
            message.reply.await_args.kwargs["allowed_mentions"].everyone
        )

    async def test_ignores_messages_from_bots(self) -> None:
        bot_user = object()
        bot = SimpleNamespace(user=bot_user, latency=0.042)
        message = SimpleNamespace(
            author=SimpleNamespace(bot=True),
            mentions=[bot_user],
            reply=AsyncMock(),
        )

        await MentionPingCog(bot).on_message(message)

        message.reply.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

