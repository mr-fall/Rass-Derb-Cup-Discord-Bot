"""Unit tests for form command input validation."""

from __future__ import annotations

import unittest

from rass_derb_bot.services.form_utils import (
    FormInputError,
    parse_color,
    parse_message_link,
    validate_image_url,
    validate_slug,
)


class FormUtilsTests(unittest.TestCase):
    def test_validates_and_normalizes_section_slug(self) -> None:
        self.assertEqual(validate_slug("Rass-Derb-QA"), "rass-derb-qa")

    def test_rejects_invalid_section_slug(self) -> None:
        with self.assertRaises(FormInputError):
            validate_slug("Rass Derb QA!")

    def test_parses_hex_color(self) -> None:
        self.assertEqual(parse_color("#2E86DE"), 0x2E86DE)

    def test_rejects_invalid_color(self) -> None:
        with self.assertRaises(FormInputError):
            parse_color("#FFF")

    def test_parses_discord_message_link(self) -> None:
        self.assertEqual(
            parse_message_link(
                "https://discord.com/channels/123/456/789?jump=true"
            ),
            (123, 456, 789),
        )

    def test_rejects_non_discord_message_link(self) -> None:
        with self.assertRaises(FormInputError):
            parse_message_link("https://example.com/channels/123/456/789")

    def test_accepts_blank_image_url_as_default_banner(self) -> None:
        self.assertIsNone(validate_image_url(""))

    def test_validates_large_image_url(self) -> None:
        self.assertEqual(
            validate_image_url("https://cdn.example.com/banner.png"),
            "https://cdn.example.com/banner.png",
        )


if __name__ == "__main__":
    unittest.main()
