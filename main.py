import discord
from discord.ext import commands
import yt_dlp
import asyncio
import time
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="+", intents=intents)

queue = {}
now_playing = {}
volume_level = {}
looping = {}

ytdlp_options = {"format": "bestaudio/best", "quiet": True}
ffmpeg_options = {"options": "-vn"}

def format_time(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def progress_bar(current, total, size=20):
    filled = int(size * current / total)
    return "█" * filled + "─" * (size - filled)

async def play_next(ctx):
    gid = ctx.guild.id
    if looping.get(gid) and gid in now_playing:
        song = now_playing[gid]
    else:
        if not queue.get(gid):
            await ctx.voice_client.disconnect()
            return
        song = queue[gid].pop(0)
        now_playing[gid] = song

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(song["url"], **ffmpeg_options),
        volume=volume_level.get(gid, 0.5)
    )

    ctx.voice_client.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(ctx), bot.loop
        )
    )

    start_time = time.time()
    embed_msg = await send_embed(ctx, song, start_time)

    while ctx.voice_client and ctx.voice_client.is_playing():
        elapsed = time.time() - start_time
        bar = progress_bar(elapsed, song["duration"])
        embed = discord.Embed(
            title="🎵 Music With Warrior",
            description=f"**{song['title']}**\n`{bar}`\n{format_time(elapsed)}/{format_time(song['duration'])}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_image(url=song["thumbnail"])
        embed.set_footer(text="Bot Dev Subhan")
        await embed_msg.edit(embed=embed)
        await asyncio.sleep(5)

async def send_embed(ctx, song, start_time):
    embed = discord.Embed(
        title="🎵 Music With Warrior",
        description=f"**{song['title']}**\n⏱ {format_time(song['duration'])}",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_image(url=song["thumbnail"])
    embed.set_footer(text="Dev by Subhan")
    view = PlayerButtons(ctx)
    return await ctx.send(embed=embed, view=view)

class PlayerButtons(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.danger)
    async def play_pause(self, interaction: discord.Interaction, button):
        if self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
        elif self.ctx.voice_client.is_paused():
            self.ctx.voice_client.resume()
        await interaction.response.defer()

    @discord.ui.button(label="Skip/Stop", style=discord.ButtonStyle.danger)
    async def skip(self, interaction: discord.Interaction, button):
        self.ctx.voice_client.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Loop ON/OFF", style=discord.ButtonStyle.danger)
    async def loop_btn(self, interaction: discord.Interaction, button):
        gid = self.ctx.guild.id
        looping[gid] = not looping.get(gid, False)
        await interaction.response.send_message(f"🔁 Loop {'ON' if looping[gid] else 'OFF'}", ephemeral=True)

    @discord.ui.button(label="Vol -", style=discord.ButtonStyle.danger)
    async def volume_down(self, interaction: discord.Interaction, button):
        gid = self.ctx.guild.id
        volume_level[gid] = max(volume_level.get(gid,0.5) - 0.1, 0)
        if self.ctx.voice_client.source:
            self.ctx.voice_client.source.volume = volume_level[gid]
        await interaction.response.defer()

    @discord.ui.button(label="Vol +", style=discord.ButtonStyle.danger)
    async def volume_up(self, interaction: discord.Interaction, button):
        gid = self.ctx.guild.id
        volume_level[gid] = min(volume_level.get(gid,0.5) + 0.1, 1)
        if self.ctx.voice_client.source:
            self.ctx.voice_client.source.volume = volume_level[gid]
        await interaction.response.defer()

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.danger)
    async def show_queue(self, interaction: discord.Interaction, button):
        q = queue.get(self.ctx.guild.id, [])
        if not q:
            await interaction.response.send_message("📭 Queue empty", ephemeral=True)
        else:
            msg = "\n".join([f"{i+1}. {s['title']}" for i,s in enumerate(q)])
            await interaction.response.send_message(f"📜 **Queue:**\n{msg}", ephemeral=True)

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice:
        return await ctx.send("❌ Voice channel join karo")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    with yt_dlp.YoutubeDL(ytdlp_options) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)
        data = info["entries"][0]

    song = {
        "url": data["url"],
        "title": data["title"],
        "duration": data.get("duration",0),
        "thumbnail": data.get("thumbnail")
    }

    queue.setdefault(ctx.guild.id, []).append(song)
    await ctx.send(f"➕ Added New Song of Your Queue**{song['title']}**")

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
        
bot.run("DISCORD_TOKEN")