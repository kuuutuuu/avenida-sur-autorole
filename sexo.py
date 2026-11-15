import logging
import os
import re
import time
from pathlib import Path

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

GUILD_ID = int(os.environ["GUILD_ID"])
EXCLUDED_CATEGORY_ID = 969498559340740648  # 📄 Información / Comandos 📄
COOLDOWN_SECONDS = 60
PATTERN = re.compile(r"\bsexo\b", re.IGNORECASE)
IMAGE_PATH = Path(__file__).parent / "assets" / "sexo.jpeg"


def _category_id(channel: discord.abc.GuildChannel) -> int | None:
    category_id = getattr(channel, "category_id", None)
    if category_id is None:
        parent = getattr(channel, "parent", None)
        category_id = getattr(parent, "category_id", None)
    return category_id


class Sexo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last: dict[int, float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        if message.author.bot:
            return
        if _category_id(message.channel) == EXCLUDED_CATEGORY_ID:
            return
        if not PATTERN.search(message.content or ""):
            return
        now = time.monotonic()
        previous = self.last.get(message.channel.id, 0.0)
        if now - previous < COOLDOWN_SECONDS:
            return
        self.last[message.channel.id] = now
        try:
            await message.channel.send(file=discord.File(IMAGE_PATH))
        except Exception:
            log.exception("No se pudo enviar la imagen de sexo")
