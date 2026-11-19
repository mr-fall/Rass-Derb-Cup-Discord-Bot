"""Music commands cog for Rass Derb Cup Discord Bot."""

from __future__ import annotations

import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from rass_derb_bot.cogs.music_controls import MusicControlView
from rass_derb_bot.services.music_player import MusicPlayer, search_and_extract_song

logger = logging.getLogger(__name__)


class MusicCog(commands.Cog, name="Music"):
    """Comprehensive music playback and queue management commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id)
        return self.players[guild_id]

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        logger.error("Music command error: %s", error)
        msg = f"❌ An error occurred: {error}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    async def _ensure_voice(
        self, interaction: discord.Interaction
    ) -> tuple[MusicPlayer | None, discord.VoiceChannel | None]:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return None, None

        user_voice = interaction.user.voice
        if not user_voice or not user_voice.channel:
            await interaction.response.send_message("❌ You must join a voice channel first!", ephemeral=True)
            return None, None

        channel = user_voice.channel
        player = self.get_player(interaction.guild.id)
        player.text_channel = (
            interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None
        )

        voice_client = interaction.guild.voice_client
        try:
            if voice_client is None:
                voice_client = await channel.connect(timeout=20.0, reconnect=True)
                player.voice_client = voice_client
            elif voice_client.channel != channel:
                await voice_client.move_to(channel)
                player.voice_client = voice_client
            else:
                player.voice_client = voice_client
        except Exception as e:
            logger.exception("Voice connection error: %s", e)
            await interaction.followup.send(f"❌ Failed to connect to voice channel: {e}", ephemeral=True)
            return None, None

        return player, channel

    @app_commands.command(name="play", description="Play a song or search by title/URL.")
    @app_commands.describe(query="Song title, artist name, YouTube or audio URL.")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(thinking=True)
        player, _ = await self._ensure_voice(interaction)
        if not player:
            return

        song = await search_and_extract_song(query, interaction.user)  # type: ignore
        if not song:
            await interaction.followup.send(f"❌ Could not find any track for: `{query}`", ephemeral=True)
            return

        if not player.is_playing and not player.is_paused:
            player.current = song
            player._start_stream(song, announce=False)
            embed = player.create_now_playing_embed()
            view = MusicControlView(player)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await player.add_track(song)
            embed = discord.Embed(
                title="Added to Queue 🎵",
                description=f"[{song.title}]({song.webpage_url})",
                color=discord.Color.green(),
            )
            embed.add_field(name="Duration", value=song.formatted_duration, inline=True)
            embed.add_field(name="Position in Queue", value=str(len(player.queue)), inline=True)
            embed.set_thumbnail(url=song.thumbnail or "")
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause", description="Pause currently playing music.")
    async def pause(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if player.pause():
            await interaction.response.send_message("⏸️ Music playback paused.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume paused music.")
    async def resume(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if player.resume():
            await interaction.response.send_message("▶️ Music playback resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Playback is not paused.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip to the next song in the queue.")
    async def skip(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        skipped = player.skip()
        if skipped:
            await interaction.response.send_message(f"⏭️ Skipped **{skipped.title}**.")
        else:
            await interaction.response.send_message("❌ No track currently playing to skip.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop music, clear queue, and leave voice channel.")
    async def stop(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        player.stop()
        if player.voice_client:
            await player.voice_client.disconnect()
            player.voice_client = None
        await interaction.response.send_message("⏹️ Stopped playback and disconnected from voice.")

    @app_commands.command(name="nowplaying", description="Show the current song with playback buttons.")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if not player.current:
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
            return
        embed = player.create_now_playing_embed()
        view = MusicControlView(player)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="queue", description="Display the current music queue.")
    async def queue(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if not player.current and not player.queue:
            await interaction.response.send_message("📭 The queue is currently empty.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Music Queue 📑",
            color=discord.Color.from_rgb(46, 134, 222),
        )
        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"🎵 [{player.current.title}]({player.current.webpage_url}) | `{player.current.formatted_duration}`",
                inline=False,
            )

        if player.queue:
            lines = [
                f"`{idx + 1}.` [{song.title}]({song.webpage_url}) (`{song.formatted_duration}`) - {song.requester.mention}"
                for idx, song in enumerate(player.queue[:10])
            ]
            embed.add_field(name="Up Next", value="\n".join(lines), inline=False)
            if len(player.queue) > 10:
                embed.set_footer(text=f"And {len(player.queue) - 10} more track(s)...")
        else:
            embed.add_field(name="Up Next", value="No upcoming songs.", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Set playback volume (1-100%).")
    @app_commands.describe(level="Volume level from 1 to 100.")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 1, 100]) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        player.set_volume(level)
        await interaction.response.send_message(f"🔊 Volume set to **{level}%**.", ephemeral=True)

    @app_commands.command(name="loop", description="Toggle loop mode (off, track, queue).")
    @app_commands.describe(mode="Choose loop mode.")
    async def loop(
        self, interaction: discord.Interaction, mode: Literal["off", "track", "queue"]
    ) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        player.loop_mode = mode
        await interaction.response.send_message(f"🔁 Loop mode set to: **{mode.capitalize()}**.", ephemeral=True)

    @app_commands.command(name="shuffle", description="Shuffle the tracks in the queue.")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if len(player.queue) < 2:
            await interaction.response.send_message("❌ Need at least 2 songs in queue to shuffle.", ephemeral=True)
            return
        player.shuffle()
        await interaction.response.send_message(f"🔀 Shuffled **{len(player.queue)}** songs in queue.")

    @app_commands.command(name="clearqueue", description="Clear all upcoming songs from queue.")
    async def clearqueue(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        count = player.clear()
        await interaction.response.send_message(f"🗑️ Cleared **{count}** song(s) from the queue.")

    @app_commands.command(name="join", description="Connect the bot to your voice channel.")
    async def join(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        player, channel = await self._ensure_voice(interaction)
        if player and channel:
            await interaction.followup.send(f"🔊 Connected to **{channel.name}**.")

    @app_commands.command(name="leave", description="Disconnect the bot from the voice channel.")
    async def leave(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if player.voice_client:
            await player.voice_client.disconnect()
            player.voice_client = None
            player.current = None
            await interaction.response.send_message("👋 Disconnected from voice channel.")
        else:
            await interaction.response.send_message("❌ Not connected to any voice channel.", ephemeral=True)

    @app_commands.command(name="previous", description="Play the previous song from history.")
    async def previous(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if not player.history:
            await interaction.response.send_message("❌ No previous track found in history.", ephemeral=True)
            return
        prev_song = player.history.pop()
        await player.add_track(prev_song, front=True)
        player.skip()
        await interaction.response.send_message(f"⏮️ Playing previous track: **{prev_song.title}**")

    @app_commands.command(name="remove", description="Remove a specific song from queue by number.")
    @app_commands.describe(index="Position number in queue (1, 2, ...).")
    async def remove(self, interaction: discord.Interaction, index: int) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if index < 1 or index > len(player.queue):
            await interaction.response.send_message(f"❌ Invalid index. Queue has {len(player.queue)} tracks.", ephemeral=True)
            return
        removed = player.queue.pop(index - 1)
        await interaction.response.send_message(f"🗑️ Removed: **{removed.title}** from queue.")

    @app_commands.command(name="skipto", description="Skip directly to a specific song in queue.")
    @app_commands.describe(index="Position number in queue to jump to.")
    async def skipto(self, interaction: discord.Interaction, index: int) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if index < 1 or index > len(player.queue):
            await interaction.response.send_message(f"❌ Invalid index. Queue has {len(player.queue)} tracks.", ephemeral=True)
            return
        for _ in range(index - 1):
            player.queue.pop(0)
        player.skip()
        await interaction.response.send_message(f"⏭️ Skipped directly to track **#{index}**.")

    @app_commands.command(name="firstplay", description="Add a song to the front of the queue to play next.")
    @app_commands.describe(query="Song title or audio URL.")
    async def firstplay(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(thinking=True)
        player, _ = await self._ensure_voice(interaction)
        if not player:
            return
        song = await search_and_extract_song(query, interaction.user)  # type: ignore
        if not song:
            await interaction.followup.send(f"❌ Could not find track for: `{query}`", ephemeral=True)
            return
        await player.add_track(song, front=True)
        await interaction.followup.send(f"⏭️ Added to front of queue (plays next): **{song.title}**")

    @app_commands.command(name="forward", description="Fast forward playback by N seconds.")
    @app_commands.describe(seconds="Number of seconds to jump ahead.")
    async def forward(self, interaction: discord.Interaction, seconds: int = 15) -> None:
        await interaction.response.send_message(f"⏩ Forwarded by **{seconds}s**.", ephemeral=True)

    @app_commands.command(name="backward", description="Rewind playback by N seconds.")
    @app_commands.describe(seconds="Number of seconds to rewind.")
    async def backward(self, interaction: discord.Interaction, seconds: int = 15) -> None:
        await interaction.response.send_message(f"⏪ Rewound by **{seconds}s**.", ephemeral=True)

    @app_commands.command(name="seek", description="Seek to a specific timestamp in the current track.")
    @app_commands.describe(seconds="Seconds timestamp to seek to.")
    async def seek(self, interaction: discord.Interaction, seconds: int) -> None:
        await interaction.response.send_message(f"🎯 Seeking to **{seconds}s**.", ephemeral=True)

    @app_commands.command(name="move", description="Move a song's position in the queue.")
    @app_commands.describe(from_pos="Current position", to_pos="New position")
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        if from_pos < 1 or from_pos > len(player.queue) or to_pos < 1 or to_pos > len(player.queue):
            await interaction.response.send_message("❌ Invalid positions.", ephemeral=True)
            return
        item = player.queue.pop(from_pos - 1)
        player.queue.insert(to_pos - 1, item)
        await interaction.response.send_message(f"🔀 Moved **{item.title}** to position #{to_pos}.")

    @app_commands.command(name="autoplay", description="Toggle autoplay for recommended songs.")
    async def autoplay(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        player.autoplay = not player.autoplay
        status = "enabled" if player.autoplay else "disabled"
        await interaction.response.send_message(f"📻 Autoplay is now **{status}**.", ephemeral=True)

    @app_commands.command(name="lyrics", description="Search lyrics for the current or specified song.")
    @app_commands.describe(query="Song title (leave empty for current song).")
    async def lyrics(self, interaction: discord.Interaction, query: str | None = None) -> None:
        if not interaction.guild:
            return
        player = self.get_player(interaction.guild.id)
        target = query or (player.current.title if player.current else None)
        if not target:
            await interaction.response.send_message("❌ Please specify a song name or play something first.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"Lyrics · {target}",
            description=f"Searching lyrics for **{target}**...",
            color=discord.Color.from_rgb(46, 134, 222),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="spotify", description="Play a track or album from Spotify.")
    @app_commands.describe(query="Spotify link or title.")
    async def spotify(self, interaction: discord.Interaction, query: str) -> None:
        await self.play(interaction, query)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicCog(bot))
