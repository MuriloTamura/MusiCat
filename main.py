import discord
from discord.ext import commands
import yt_dlp
import asyncio
import logging
from dotenv import load_dotenv
import os
from collections import deque

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── State per guild ───────────────────────────────────────────────────────────
# { guild_id: { "queue": deque, "current": dict | None, "loop": bool } }
guild_state: dict[int, dict] = {}

def get_state(guild_id: int) -> dict:
    if guild_id not in guild_state:
        guild_state[guild_id] = {"queue": deque(), "current": None, "loop": False}
    return guild_state[guild_id]

# ── yt-dlp helpers ────────────────────────────────────────────────────────────
YTDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",   # aceita nome da música também
    "source_address": "0.0.0.0",
}

FFMPEG_OPTS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ),
    "options": "-vn",
}

async def fetch_info(query: str) -> dict | None:
    """Extrai informações do vídeo/áudio sem baixar."""
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        try:
            data = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )
        except yt_dlp.utils.DownloadError:
            return None

    # Se vier uma playlist (search), pega o primeiro resultado
    if "entries" in data:
        data = data["entries"][0]

    return {
        "title": data.get("title", "Desconhecido"),
        "url": data["url"],
        "webpage_url": data.get("webpage_url", query),
        "duration": data.get("duration", 0),
        "thumbnail": data.get("thumbnail"),
    }

def fmt_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

# ── Playback engine ───────────────────────────────────────────────────────────
async def play_next(ctx: commands.Context):
    state = get_state(ctx.guild.id)
    vc: discord.VoiceClient = ctx.voice_client

    if not vc or not vc.is_connected():
        return

    # Loop: recoloca a música atual na frente da fila
    if state["loop"] and state["current"]:
        state["queue"].appendleft(state["current"])

    if not state["queue"]:
        state["current"] = None
        await ctx.send("✅ Fila vazia — reprodução encerrada.")
        return

    track = state["queue"].popleft()
    state["current"] = track

    source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS)
    source = discord.PCMVolumeTransformer(source, volume=0.8)

    def after(error):
        if error:
            logging.error(f"Erro na reprodução: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    vc.play(source, after=after)

    embed = discord.Embed(
        title="🎵 Tocando agora",
        description=f"[{track['title']}]({track['webpage_url']})",
        color=discord.Color.green(),
    )
    embed.add_field(name="Duração", value=fmt_duration(track["duration"]))
    if track["thumbnail"]:
        embed.set_thumbnail(url=track["thumbnail"])
    await ctx.send(embed=embed)

# ── Commands ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")

@bot.command(aliases=["p"])
async def play(ctx: commands.Context, *, query: str):
    """Toca ou adiciona à fila. Aceita URL ou nome da música."""
    if not ctx.author.voice:
        return await ctx.send("❌ Você precisa estar em um canal de voz.")

    channel = ctx.author.voice.channel
    vc = ctx.voice_client

    if vc is None:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)

    async with ctx.typing():
        track = await fetch_info(query)

    if not track:
        return await ctx.send("❌ Não consegui encontrar a música.")

    state = get_state(ctx.guild.id)
    state["queue"].append(track)

    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)
    else:
        pos = len(state["queue"])
        await ctx.send(
            f"➕ **{track['title']}** adicionada à fila (posição {pos}) — {fmt_duration(track['duration'])}"
        )

@bot.command()
async def skip(ctx: commands.Context):
    """Pula a música atual."""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Pulando...")
    else:
        await ctx.send("❌ Nenhuma música tocando.")

@bot.command()
async def pause(ctx: commands.Context):
    """Pausa a reprodução."""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Pausado.")
    else:
        await ctx.send("❌ Nenhuma música tocando.")

@bot.command(aliases=["resume"])
async def unpause(ctx: commands.Context):
    """Retoma a reprodução."""
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Retomando.")
    else:
        await ctx.send("❌ A música não está pausada.")

@bot.command()
async def stop(ctx: commands.Context):
    """Para tudo e limpa a fila."""
    state = get_state(ctx.guild.id)
    state["queue"].clear()
    state["current"] = None
    vc = ctx.voice_client
    if vc:
        vc.stop()
        await vc.disconnect()
    await ctx.send("⏹️ Parado e desconectado.")

@bot.command(aliases=["q"])
async def queue(ctx: commands.Context):
    """Mostra a fila de músicas."""
    state = get_state(ctx.guild.id)
    current = state["current"]
    q = state["queue"]

    if not current and not q:
        return await ctx.send("📭 A fila está vazia.")

    lines = []
    if current:
        lines.append(f"**▶️ Agora:** {current['title']} ({fmt_duration(current['duration'])})")
    for i, t in enumerate(q, 1):
        lines.append(f"**{i}.** {t['title']} ({fmt_duration(t['duration'])})")
        if i >= 10:
            lines.append(f"… e mais {len(q) - 10} músicas")
            break

    embed = discord.Embed(
        title="🎶 Fila de reprodução",
        description="\n".join(lines),
        color=discord.Color.blurple(),
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["np", "current"])
async def nowplaying(ctx: commands.Context):
    """Mostra a música que está tocando agora."""
    state = get_state(ctx.guild.id)
    track = state["current"]
    if not track:
        return await ctx.send("❌ Nenhuma música tocando.")

    embed = discord.Embed(
        title="🎵 Tocando agora",
        description=f"[{track['title']}]({track['webpage_url']})",
        color=discord.Color.green(),
    )
    embed.add_field(name="Duração", value=fmt_duration(track["duration"]))
    if track["thumbnail"]:
        embed.set_thumbnail(url=track["thumbnail"])
    await ctx.send(embed=embed)

@bot.command()
async def loop(ctx: commands.Context):
    """Ativa/desativa o loop da música atual."""
    state = get_state(ctx.guild.id)
    state["loop"] = not state["loop"]
    status = "🔁 Loop **ativado**." if state["loop"] else "➡️ Loop **desativado**."
    await ctx.send(status)

@bot.command()
async def volume(ctx: commands.Context, vol: int):
    """Ajusta o volume (0-100)."""
    vc = ctx.voice_client
    if not vc or not vc.source:
        return await ctx.send("❌ Nenhuma música tocando.")
    if not 0 <= vol <= 100:
        return await ctx.send("❌ Volume deve ser entre 0 e 100.")
    vc.source.volume = vol / 100
    await ctx.send(f"🔊 Volume ajustado para **{vol}%**.")

@bot.command()
async def remove(ctx: commands.Context, pos: int):
    """Remove uma música da fila pelo número."""
    state = get_state(ctx.guild.id)
    q = state["queue"]
    if pos < 1 or pos > len(q):
        return await ctx.send("❌ Posição inválida.")
    q_list = list(q)
    removed = q_list.pop(pos - 1)
    state["queue"] = deque(q_list)
    await ctx.send(f"🗑️ Removido: **{removed['title']}**")

@bot.command(aliases=["commands", "ajuda"])
async def help_bot(ctx: commands.Context):
    """Lista todos os comandos."""
    embed = discord.Embed(title="🎵 Comandos do Bot de Música", color=discord.Color.purple())
    cmds = {
        "!play <nome ou URL>": "Toca ou adiciona à fila",
        "!skip": "Pula a música atual",
        "!pause": "Pausa a reprodução",
        "!resume": "Retoma a reprodução",
        "!stop": "Para tudo e desconecta",
        "!queue": "Mostra a fila",
        "!nowplaying": "Música atual",
        "!loop": "Ativa/desativa loop",
        "!volume <0-100>": "Ajusta o volume",
        "!remove <nº>": "Remove da fila",
    }
    for cmd, desc in cmds.items():
        embed.add_field(name=cmd, value=desc, inline=False)
    await ctx.send(embed=embed)

# ── Error handler ─────────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando. Use `!help_bot` para ver os comandos.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # ignora comandos desconhecidos silenciosamente
    else:
        logging.error(f"Erro no comando {ctx.command}: {error}")
        await ctx.send(f"❌ Erro inesperado: `{error}`")

# ── Run ───────────────────────────────────────────────────────────────────────
bot.run(TOKEN, log_handler=handler, log_level=logging.INFO)