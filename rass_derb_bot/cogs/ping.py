"""Respond to mentions with boss greetings, latency stats, or Moroccan banter."""

from __future__ import annotations

import random
import re

import discord
from discord.ext import commands

from rass_derb_bot.services.ping import format_ping

BOSS_USER_ID = 922592319826427955

BOSS_REPLIES = [
    "N3am a sidi! 👑",
    "N3am a chef! Marhba bik 🙌",
    "Llay barek f 3mr sidi! Khedam 3la wdek 🫡",
    "Merhba b l-boss dyalna! Ash kat-amer a chef? ✨",
]

DISRESPECT_PATTERNS = re.compile(r"\b(xkon|chkon|chkoun|xkun|who)\s+(nta|ntaya|you)\b", re.IGNORECASE)

SAVAGE_REPLIES = [
    "Li 7wak! ... Wa ta sir layhdik chouf khedma l rask 😂",
    "Ana l-bot dyal Rass Derb Cup w syadk! Nta chkon daha fik? 🥱",
]

GENERAL_USER_REPLIES = [
    "Hta tkoun qad syadk 3ad aji dwi m3aya 😉",
    "Mat-déronjinch db, rani m3a sidi w chef dyali 👑",
    "Sir hta tkber 3ad aji t-tagini 🤫",
]


class MentionPingCog(commands.Cog):
    """Handle bot mentions and fun Moroccan interactions."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.bot.user is None:
            return
        if self.bot.user not in message.mentions:
            return

        content = message.content.lower()

        # If user is the Boss
        if message.author.id == BOSS_USER_ID:
            reply = random.choice(BOSS_REPLIES)
            await message.reply(reply, mention_author=True)
            return

        # If someone else asked who the bot is or trash-talked
        if DISRESPECT_PATTERNS.search(content):
            reply = random.choice(SAVAGE_REPLIES)
            await message.reply(reply, mention_author=True)
            return

        # If they specifically asked for ping/latency
        if "ping" in content or "ms" in content or "latency" in content:
            await message.reply(format_ping(self.bot.latency), mention_author=False)
            return

        # General mention by anyone else
        reply = random.choice(GENERAL_USER_REPLIES)
        await message.reply(reply, mention_author=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MentionPingCog(bot))
