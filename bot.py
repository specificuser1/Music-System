import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
import asyncio
import os
import json

# ==============================
# LOAD ENV
# ==============================

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ==============================
# LOAD CONFIG
# ==============================

with open("config.json") as f:
    config = json.load(f)

PREFIX = config["prefix"]
DEFAULT_VOLUME = config["volume"]

# ==============================
# BOT SETUP
# ==============================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

queue = []

# ==============================
# YTDL OPTIONS
# ==============================

ytdl_format_options = {
    'format': 'bestaudio',
    'quiet': True
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# ==============================
# SAVE HISTORY
# ==============================

def save_history(title):
    with open("data/history.txt", "a", encoding="utf8") as f:
        f.write(title + "\n")

# ==============================
# EVENTS
# ==============================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ==============================
# JOIN
# ==============================

@bot.command()
async def join(ctx):
    try:
        if ctx.author.voice is None:
            await ctx.send("❌ You must be in a voice channel.")
            return

        channel = ctx.author.voice.channel

        if ctx.voice_client is None:
            await channel.connect()
        else:
            await ctx.voice_client.move_to(channel)

        await ctx.send("✅ Joined voice channel")

    except Exception as e:
        await ctx.send(f"Error: {e}")

# ==============================
# PLAY
# ==============================

@bot.command()
async def play(ctx, *, search):

    if ctx.author.voice is None:
        await ctx.send("❌ Join a voice channel first")
        return

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()

    try:

        loop = asyncio.get_event_loop()

        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(
            f"ytsearch:{search}",
            download=False
        ))

        song = data['entries'][0]

        url = song['url']
        title = song['title']

        queue.append((url, title))
        save_history(title)

        await ctx.send(f"🎶 Added to queue: **{title}**")

        if not ctx.voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f"❌ Play Error: {e}")

# ==============================
# PLAY NEXT
# ==============================

async def play_next(ctx):

    if len(queue) == 0:
        return

    url, title = queue.pop(0)

    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

    ctx.voice_client.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )

    await ctx.send(f"▶ Now playing: **{title}**")

# ==============================
# SKIP
# ==============================

@bot.command()
async def skip(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Skipped")

# ==============================
# STOP
# ==============================

@bot.command()
async def stop(ctx):

    queue.clear()

    if ctx.voice_client:
        await ctx.voice_client.disconnect()

    await ctx.send("⏹ Music stopped")

# ==============================
# QUEUE
# ==============================

@bot.command()
async def queue(ctx):

    if not queue:
        await ctx.send("Queue empty")
        return

    msg = "\n".join([f"{i+1}. {song[1]}" for i, song in enumerate(queue)])

    await ctx.send(f"📜 Queue:\n{msg}")

# ==============================
# ERROR HANDLER
# ==============================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    await ctx.send(f"⚠ Error: {str(error)}")

# ==============================
# RUN
# ==============================

bot.run(TOKEN)