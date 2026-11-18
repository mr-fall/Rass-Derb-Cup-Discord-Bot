"""Unit tests for custom message payload parsing and validation."""

from __future__ import annotations

import unittest

from rass_derb_bot.services.embed_payload import (
    EmbedPayloadError,
    parse_embed_payload,
)


class ParseEmbedPayloadTests(unittest.TestCase):
    def test_content_only_message(self) -> None:
        content, embeds = parse_embed_payload('{"content":"Hello, Rass Derb!"}')
        self.assertEqual(content, "Hello, Rass Derb!")
        self.assertEqual(embeds, [])

    def test_top_level_embed_fields_and_hex_color(self) -> None:
        content, embeds = parse_embed_payload(
            '{"title":"Cup update","description":"The event is live.",'
            '"color":"#2E86DE","fields":[{"name":"Stage","value":"Final"}]}'
        )
        self.assertIsNone(content)
        self.assertEqual(len(embeds), 1)
        self.assertEqual(embeds[0].title, "Cup update")
        self.assertEqual(embeds[0].color.value, 0x2E86DE)
        self.assertEqual(embeds[0].fields[0].value, "Final")

    def test_embed_array_accepts_animated_image_url(self) -> None:
        content, embeds = parse_embed_payload(
            '{"content":"Announcement","embeds":[{"title":"Rass Derb Cup",'
            '"image":{"url":"https://cdn.example.com/banner.gif"},'
            '"footer":{"text":"Esports PUBG MOBILE MEA"}}]}'
        )
        self.assertEqual(content, "Announcement")
        self.assertEqual(embeds[0].image.url, "https://cdn.example.com/banner.gif")

    def test_image_url_shortcut(self) -> None:
        _, embeds = parse_embed_payload(
            '{"title":"Banner","image_url":"https://cdn.example.com/banner.gif"}'
        )
        self.assertEqual(embeds[0].image.url, "https://cdn.example.com/banner.gif")

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(EmbedPayloadError, "JSON syntax error"):
            parse_embed_payload("{not json}")

    def test_rejects_unsupported_top_level_key(self) -> None:
        with self.assertRaisesRegex(EmbedPayloadError, "unsupported top-level key"):
            parse_embed_payload('{"content":"Hi","components":[]}')

    def test_rejects_invalid_image_url(self) -> None:
        with self.assertRaisesRegex(EmbedPayloadError, "full http"):
            parse_embed_payload('{"title":"Banner","image_url":"javascript:alert(1)"}')

    def test_rejects_conflicting_embed_shapes(self) -> None:
        with self.assertRaisesRegex(EmbedPayloadError, "not both"):
            parse_embed_payload('{"title":"Title","embeds":[{"description":"Body"}]}')

    def test_rejects_empty_payload(self) -> None:
        with self.assertRaisesRegex(EmbedPayloadError, "include 'content'"):
            parse_embed_payload("{}")


if __name__ == "__main__":
    unittest.main()

