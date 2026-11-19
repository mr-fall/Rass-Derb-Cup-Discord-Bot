"""Music player service for Discord voice streaming with queue management."""

from __future__ import annotations

import asyncio
import logging
import random
import shutil
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import discord
import yt_dlp

logger = logging.getLogger(__name__)

# Find ffmpeg binary
venv_ffmpeg = Path(__file__).resolve().parents[2] / ".venv" / "Scripts" / "ffmpeg.exe"
if venv_ffmpeg.is_file():
    FFMPEG_PATH = str(venv_ffmpeg)
else:
    FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"

FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"

YTDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}


@dataclass
class Song:
    title: str
    webpage_url: str
    stream_url: str
    duration: int
    thumbnail: str | None
    uploader: str | None
    requester: discord.Member

    @property
    def formatted_duration(self) -> str:
        if not self.duration:
            return "Live"
        return str(timedelta(seconds=self.duration))


class MusicPlayer:
    """Manages audio playback, queue, and controls for a single Discord guild."""

    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id
        self.queue: list[Song] = []
        self.history: list[Song] = []
        self.current: Song | None = None
        self.loop_mode: str = "off"  # "off", "track", "queue"
        self.volume: float = 0.8
        self.voice_client: discord.VoiceClient | None = None
        self.autoplay: bool = False
        self.lock = asyncio.Lock()
        self.text_channel: discord.TextChannel | None = None

    @property
    def is_playing(self) -> bool:
        return self.voice_client is not None and self.voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self.voice_client is not None and self.voice_client.is_paused()

    async def add_track(self, song: Song, front: bool = False) -> None:
        if front:
            self.queue.insert(0, song)
        else:
            self.queue.append(song)

    def play_next(self, error: Exception | None = None) -> None:
        if error:
            logger.error("Player error in guild %s: %s", self.guild_id, error)

        if not self.voice_client or not self.voice_client.is_connected():
            return

        # Handle loop track
        if self.loop_mode == "track" and self.current is not None:
            self.queue.insert(0, self.current)
        elif self.loop_mode == "queue" and self.current is not None:
            self.queue.append(self.current)

        if self.current:
            self.history.append(self.current)
            if len(self.history) > 50:
                self.history.pop(0)

        if not self.queue:
            self.current = None
            if self.text_channel:
                asyncio.run_coroutine_threadsafe(
                    self.text_channel.send(
                        "🎵 Queue is empty.",
                        delete_after=10,
                    ),
                    self.voice_client.loop,
                )
            return

        self.current = self.queue.pop(0)
        self._start_stream(self.current, announce=True)

    def _start_stream(self, song: Song, announce: bool = False) -> None:
        if not self.voice_client or not self.voice_client.is_connected():
            return

        try:
            stream_url = song.stream_url
            if not stream_url or "manifest" in stream_url:
                with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
                    info = ydl.extract_info(song.webpage_url, download=False)
                    if info:
                        stream_url = extract_best_stream_url(info) or song.webpage_url
                        song.stream_url = stream_url

            source = discord.FFmpegPCMAudio(
                stream_url,
                executable=FFMPEG_PATH,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS,
            )
            transformed = discord.PCMVolumeTransformer(source, volume=self.volume)
            self.voice_client.play(transformed, after=self.play_next)

            # Send now playing notification when advancing through queue automatically
            if announce and self.text_channel:
                embed = self.create_now_playing_embed()
                from rass_derb_bot.cogs.music_controls import MusicControlView
                view = MusicControlView(self)
                asyncio.run_coroutine_threadsafe(
                    self.text_channel.send(embed=embed, view=view),
                    self.voice_client.loop,
                )
        except Exception:
            logger.exception("Failed to start audio stream.")
            self.play_next()

    def create_now_playing_embed(self) -> discord.Embed:
        if not self.current:
            return discord.Embed(
                title="Now Playing",
                description="No music is currently playing.",
                color=discord.Color.blue(),
            )
        song = self.current
        embed = discord.Embed(
            title="Now Playing 🎵",
            description=f"[{song.title}]({song.webpage_url})",
            color=discord.Color.from_rgb(46, 134, 222),
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)

        embed.add_field(name="Duration", value=song.formatted_duration, inline=True)
        embed.add_field(name="Requested By", value=song.requester.mention, inline=True)
        embed.add_field(name="Loop", value=self.loop_mode.capitalize(), inline=True)
        embed.add_field(name="Volume", value=f"{int(self.volume * 100)}%", inline=True)
        embed.add_field(name="Queue", value=f"{len(self.queue)} track(s)", inline=True)
        embed.set_footer(text="Rass Derb Cup Music System ✨")
        return embed

    def skip(self) -> Song | None:
        if not self.voice_client or not self.voice_client.is_playing():
            return None
        skipped = self.current
        self.voice_client.stop()
        return skipped

    def pause(self) -> bool:
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            return True
        return False

    def resume(self) -> bool:
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            return True
        return False

    def stop(self) -> None:
        self.queue.clear()
        self.current = None
        if self.voice_client:
            self.voice_client.stop()

    def set_volume(self, volume: int) -> None:
        clamped = max(0, min(100, volume))
        self.volume = clamped / 100.0
        if self.voice_client and self.voice_client.source:
            if hasattr(self.voice_client.source, "volume"):
                self.voice_client.source.volume = self.volume

    def shuffle(self) -> None:
        random.shuffle(self.queue)

    def clear(self) -> int:
        count = len(self.queue)
        self.queue.clear()
        return count


def extract_best_stream_url(info: dict[str, Any]) -> str:
    """Extract direct audio stream URL with highest audio bitrate from yt-dlp info."""
    formats = info.get("formats", [])
    audio_formats = [
        f for f in formats
        if f.get("acodec") != "none" and f.get("url") and not f.get("manifest_url")
    ]
    if audio_formats:
        audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
        return str(audio_formats[0]["url"])
    return str(info.get("url", ""))


async def search_and_extract_song(query: str, requester: discord.Member) -> Song | None:
    """Extract track metadata and stream URL via yt-dlp in a background thread."""
    def _extract() -> Song | None:
        opts = dict(YTDL_OPTS)
        search_query = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
            except Exception as e:
                logger.error("yt-dlp extract error: %s", e)
                return None

            if not info:
                return None

            entry = info
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                if not entries:
                    return None
                entry = entries[0]

            stream_url = extract_best_stream_url(entry)
            if not stream_url:
                stream_url = entry.get("url", "")

            return Song(
                title=entry.get("title", "Unknown Title"),
                webpage_url=entry.get("webpage_url") or entry.get("url") or query,
                stream_url=stream_url,
                duration=int(entry.get("duration") or 0),
                thumbnail=entry.get("thumbnail"),
                uploader=entry.get("uploader"),
                requester=requester,
            )

    return await asyncio.to_thread(_extract)
