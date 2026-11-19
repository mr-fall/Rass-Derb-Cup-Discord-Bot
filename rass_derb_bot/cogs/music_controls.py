"""Interactive button controls for the currently playing music track."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from rass_derb_bot.services.music_player import MusicPlayer


class MusicControlView(discord.ui.View):
    def __init__(self, player: MusicPlayer) -> None:
        super().__init__(timeout=300)
        self.player = player
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.pause_resume_button.label = "Resume" if self.player.is_paused else "Pause"
        self.pause_resume_button.emoji = "▶️" if self.player.is_paused else "⏸️"
        self.pause_resume_button.style = (
            discord.ButtonStyle.success if self.player.is_paused else discord.ButtonStyle.secondary
        )

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self.player.history:
            await interaction.response.send_message("No previous song in history.", ephemeral=True)
            return
        prev_song = self.player.history.pop()
        await self.player.add_track(prev_song, front=True)
        self.player.skip()
        await interaction.response.send_message(f"⏮️ Playing previous track: **{prev_song.title}**", ephemeral=True)

    @discord.ui.button(emoji="⏸️", label="Pause", style=discord.ButtonStyle.secondary, row=0)
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.player.is_paused:
            self.player.resume()
            self._update_buttons()
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("▶️ Resumed music playback.", ephemeral=True)
        elif self.player.is_playing:
            self.player.pause()
            self._update_buttons()
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("⏸️ Paused music playback.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", label="Skip", style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        skipped = self.player.skip()
        if skipped:
            await interaction.response.send_message(f"⏭️ Skipped: **{skipped.title}**", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @discord.ui.button(emoji="⏹️", label="Stop", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.stop()
        if self.player.voice_client:
            await self.player.voice_client.disconnect()
            self.player.voice_client = None
        await interaction.response.send_message("⏹️ Stopped playback and left the voice channel.", ephemeral=True)

    @discord.ui.button(emoji="🔀", label="Shuffle", style=discord.ButtonStyle.secondary, row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if len(self.player.queue) < 2:
            await interaction.response.send_message("Need at least 2 songs in the queue to shuffle.", ephemeral=True)
            return
        self.player.shuffle()
        await interaction.response.send_message(f"🔀 Shuffled {len(self.player.queue)} songs in the queue.", ephemeral=True)

    @discord.ui.button(emoji="🔁", label="Loop", style=discord.ButtonStyle.secondary, row=1)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modes = ["off", "track", "queue"]
        next_idx = (modes.index(self.player.loop_mode) + 1) % len(modes)
        self.player.loop_mode = modes[next_idx]
        button.label = f"Loop: {self.player.loop_mode.capitalize()}"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🔁 Loop mode set to: **{self.player.loop_mode.capitalize()}**", ephemeral=True)
