"""Interactive Help command with category dropdown menus matching the reference design."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

DEFAULT_HELP_BANNER = "https://cdn.discordapp.com/attachments/1570837395190976583/1572417416254722139/image.png?ex=6afef416&is=6afda296&hm=7eb08b1e535da10bc9fab2e3219d576fe0d8564970a7d13e12f8eba337a6b987&animated=true"

CATEGORY_COMMANDS = {
    "music": [
        "play", "pause", "resume", "skip", "stop", "nowplaying",
        "queue", "volume", "loop", "shuffle", "clear", "join",
        "leave", "previous", "remove", "skipto"
    ],
    "information": ["help", "ping"],
    "forms": ["embed", "form-section", "form-question", "setup-form", "button-form", "edit-form"],
    "settings": ["setup-form", "edit-form", "volume", "loop"],
}


class HelpCategorySelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Home Menu",
                value="home",
                description="Return to the main help panel.",
                emoji="🏠",
            ),
            discord.SelectOption(
                label="Information",
                value="information",
                description="General bot information and latency.",
                emoji="ℹ️",
            ),
            discord.SelectOption(
                label="Music",
                value="music",
                description="View all core music commands.",
                emoji="🎵",
            ),
            discord.SelectOption(
                label="Forms & Embeds",
                value="forms",
                description="Tournament forms and announcement embeds.",
                emoji="🌐",
            ),
            discord.SelectOption(
                label="Settings",
                value="settings",
                description="Configuration and admin setup.",
                emoji="⚙️",
            ),
        ]
        super().__init__(
            placeholder="🎧 | Select to view the commands.",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]
        bot_user = interaction.client.user

        if selected == "home":
            embed = build_home_embed(bot_user)
            await interaction.response.edit_message(embed=embed, view=self.view)
            return

        embed = build_category_embed(selected, bot_user)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=300)
        self.add_item(HelpCategorySelect())


def build_home_embed(bot_user: discord.User | discord.ClientUser | None) -> discord.Embed:
    bot_name = bot_user.name if bot_user else "Rass Derb Bot"
    embed = discord.Embed(
        title=f"{bot_name} ✨ Help Panel",
        color=discord.Color.from_rgb(46, 134, 222),
    )
    if bot_user and bot_user.display_avatar:
        embed.set_author(name=f"{bot_name} ✨ Help Panel", icon_url=bot_user.display_avatar.url)
        embed.set_thumbnail(url=bot_user.display_avatar.url)

    embed.add_field(
        name="🚀 How to play music",
        value="`/play <name/url>`",
        inline=False,
    )
    embed.add_field(
        name=f"❓ What is {bot_name}?",
        value=(
            "A Next-Generation Discord Bot With Many Awesome Features, Buttons, Menus, "
            "Music System, Tournament Forms, and Customizable Settings."
        ),
        inline=False,
    )
    embed.add_field(
        name="🎛 Command Categories:",
        value=(
            "ℹ️ : **Information**\n"
            "🎵 : **Music**\n"
            "🌐 : **Forms & Embeds**\n"
            "⚙️ : **Settings**"
        ),
        inline=False,
    )
    embed.set_image(url=DEFAULT_HELP_BANNER)
    if bot_user and bot_user.display_avatar:
        embed.set_footer(text=f"Thank you for selecting {bot_name} ✨!", icon_url=bot_user.display_avatar.url)
    else:
        embed.set_footer(text=f"Thank you for selecting {bot_name} ✨!")
    return embed


def build_category_embed(
    category_key: str, bot_user: discord.User | discord.ClientUser | None
) -> discord.Embed:
    titles = {
        "music": "Categories » Music",
        "information": "Categories » Information",
        "forms": "Categories » Forms & Embeds",
        "settings": "Categories » Settings",
    }
    title = titles.get(category_key, f"Categories » {category_key.capitalize()}")
    cmd_list = CATEGORY_COMMANDS.get(category_key, [])

    embed = discord.Embed(
        title=title,
        description="```\nHere are the " + category_key + " commands:\n```",
        color=discord.Color.from_rgb(46, 134, 222),
    )
    if bot_user and bot_user.display_avatar:
        embed.set_thumbnail(url=bot_user.display_avatar.url)

    formatted_cmds = " ".join(f"`{cmd}`" for cmd in cmd_list)
    embed.add_field(
        name=f"🎵 Commands Total [ {len(cmd_list)} ]",
        value=formatted_cmds or "No commands available.",
        inline=False,
    )
    embed.set_image(url=DEFAULT_HELP_BANNER)
    return embed


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="help",
        description="View the interactive help menu with all commands and music system.",
    )
    async def help(self, interaction: discord.Interaction) -> None:
        embed = build_home_embed(self.bot.user)
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
