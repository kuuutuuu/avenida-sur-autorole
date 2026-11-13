import os
import re
import time
from pathlib import Path

import discord
from discord.ext import commands

GUILD_ID = int(os.environ["GUILD_ID"])
TEST_ONLY = True
TEST_CHANNEL_ID = 1569886467138781286  # #ojo-de-pollita-👁️
COOLDOWN_SECONDS = 60
PATTERN = re.compile(r"\bsexo\b", re.IGNORECASE)
IMAGE_PATH = Path(__file__).parent / "assets" / "sexo.jpeg"


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
        if TEST_ONLY and message.channel.id != TEST_CHANNEL_ID:
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
            pass
