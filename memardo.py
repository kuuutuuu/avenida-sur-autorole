import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks

import content
import db

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)
OWNER_ID = int(os.environ.get("OWNER_ID", "310866269299671052"))
JIJI_CHANNEL_ID = 1286446347293032620
TZ = ZoneInfo("America/Caracas")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")


def image_extension(url: str, content_type: str) -> str:
    ct = (content_type or "").lower()
    if "gif" in ct:
        return ".gif"
    if "png" in ct:
        return ".png"
    if "webp" in ct:
        return ".webp"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    clean = url.lower().split("?")[0]
    for ext in (".gif", ".png", ".webp", ".jpg", ".jpeg"):
        if clean.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".png"


async def fetch_cuantocabron(session: aiohttp.ClientSession):
    async with session.get(
        "https://www.cuantocabron.com/top/dia",
        headers={"User-Agent": UA},
    ) as response:
        response.raise_for_status()
        html = await response.text()
    soup = BeautifulSoup(html, "html.parser")
    for story in soup.select("div.box.story"):
        link = story.select_one("h2.storyTitle a")
        image = story.select_one("p.story_content img")
        if link is None or image is None:
            continue
        source = image.get("src")
        if not source:
            continue
        title = link.get_text(strip=True)
        page_url = link.get("href") or ""
        if page_url.startswith("/"):
            page_url = "https://www.cuantocabron.com" + page_url
        return title, page_url, source
    raise RuntimeError("CuantoCabron sin imagen")


async def fetch_reddit(session: aiohttp.ClientSession):
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise RuntimeError("Reddit sin credenciales")
    auth = aiohttp.BasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    async with session.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=auth,
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": UA},
    ) as response:
        response.raise_for_status()
        token = (await response.json())["access_token"]
    async with session.get(
        "https://oauth.reddit.com/r/BuenosMemesEsp/top",
        params={"t": "day", "limit": 10},
        headers={"Authorization": f"bearer {token}", "User-Agent": UA},
    ) as response:
        response.raise_for_status()
        payload = await response.json()
    for child in payload["data"]["children"]:
        post = child["data"]
        image_url = post.get("url_overridden_by_dest") or post.get("url")
        if not image_url:
            continue
        clean = image_url.lower().split("?")[0]
        if not any(
            clean.endswith(ext)
            for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")
        ):
            continue
        title = post.get("title", "")
        permalink = "https://www.reddit.com" + post.get("permalink", "")
        return title, permalink, image_url
    raise RuntimeError("Reddit sin imagen")


async def download_image(session: aiohttp.ClientSession, url: str):
    async with session.get(url, headers={"User-Agent": UA}) as response:
        response.raise_for_status()
        data = await response.read()
        if len(data) > 8 * 1024 * 1024:
            raise RuntimeError("imagen demasiado grande")
        return data, image_extension(url, response.headers.get("Content-Type", ""))


def source_callback(source: str, label: str):
    async def callback(interaction: discord.Interaction) -> None:
        pool = db.pool()
        if pool is not None:
            try:
                await pool.execute(
                    "INSERT INTO settings (key, value) VALUES ('memardo_source', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                    source,
                )
            except Exception:
                pass
        await interaction.response.send_message(
            content.MEMARDO_SOURCE_CHANGED.format(fuente=label),
            ephemeral=True,
        )

    return callback


class Memardo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_unload(self) -> None:
        self.daily.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.daily.is_running():
            self.daily.start()

    @tasks.loop(minutes=30)
    async def daily(self) -> None:
        now = datetime.now(TZ)
        if now.hour < 12:
            return
        pool = db.pool()
        if pool is None:
            return
        try:
            posted = await pool.fetchval(
                "SELECT 1 FROM daily_memes WHERE meme_date=$1", now.date()
            )
        except Exception:
            return
        if posted:
            return
        await self.publish(forced=False)

    @daily.before_loop
    async def before_daily(self) -> None:
        await self.bot.wait_until_ready()

    async def get_source(self) -> str:
        pool = db.pool()
        if pool is None:
            return "cuantocabron"
        try:
            value = await pool.fetchval(
                "SELECT value FROM settings WHERE key='memardo_source'"
            )
        except Exception:
            value = None
        return value or "cuantocabron"

    async def publish(self, forced: bool) -> tuple[bool, str]:
        pool = db.pool()
        if pool is None:
            return False, content.VESTIDOR_ERR_GENERIC
        source = await self.get_source()
        today = datetime.now(TZ).date()
        if not forced:
            try:
                if await pool.fetchval(
                    "SELECT 1 FROM daily_memes WHERE meme_date=$1", today
                ):
                    return True, ""
            except Exception:
                pass
        channel = self.bot.get_channel(JIJI_CHANNEL_ID)
        if channel is None:
            return False, content.VESTIDOR_ERR_GENERIC
        try:
            async with aiohttp.ClientSession() as session:
                if source == "reddit":
                    title, page_url, image_url = await fetch_reddit(session)
                else:
                    title, page_url, image_url = await fetch_cuantocabron(session)
                image_bytes, extension = await download_image(session, image_url)
            thread = await channel.create_thread(
                name=content.MEMARDO_THREAD,
                type=discord.ChannelType.private_thread,
                invitable=False,
                reason="Memardo del día",
            )
            owner = self.bot.get_user(OWNER_ID)
            if owner is not None:
                try:
                    await thread.add_user(owner)
                except Exception:
                    pass
            filename = f"meme{extension}"
            embed = discord.Embed(
                title=content.MEMARDO_TITLE,
                description=title[:200] if title else None,
                url=page_url,
                color=0x90A4AE,
            )
            embed.set_image(url=f"attachment://{filename}")
            await thread.send(
                embed=embed,
                file=discord.File(io.BytesIO(image_bytes), filename=filename),
            )
            await pool.execute(
                "INSERT INTO daily_memes (meme_date, source, title, url) "
                "VALUES ($1,$2,$3,$4) ON CONFLICT (meme_date) DO NOTHING",
                today,
                source,
                title[:200] if title else None,
                page_url,
            )
            return True, ""
        except Exception as exc:
            return False, str(exc)

    @app_commands.command(name="memardo", description=content.MEMARDO_CMD_DESC)
    @app_commands.guilds(GUILD_OBJ)
    @app_commands.default_permissions(administrator=True)
    async def memardo(self, interaction: discord.Interaction) -> None:
        view = discord.ui.View(timeout=300)
        button_cc = discord.ui.Button(
            label=content.MEMARDO_SOURCE_CC,
            style=discord.ButtonStyle.secondary,
        )
        button_cc.callback = source_callback(
            "cuantocabron", content.MEMARDO_SOURCE_CC
        )
        view.add_item(button_cc)
        if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
            button_reddit = discord.ui.Button(
                label=content.MEMARDO_SOURCE_REDDIT,
                style=discord.ButtonStyle.secondary,
            )
            button_reddit.callback = source_callback(
                "reddit", content.MEMARDO_SOURCE_REDDIT
            )
            view.add_item(button_reddit)
        button_now = discord.ui.Button(
            label=content.MEMARDO_NOW,
            style=discord.ButtonStyle.primary,
        )

        async def now_callback(interaction_now: discord.Interaction) -> None:
            await interaction_now.response.defer(ephemeral=True)
            ok, _ = await self.publish(forced=True)
            if ok:
                await interaction_now.followup.send("✅", ephemeral=True)
            else:
                await interaction_now.followup.send(
                    content.VESTIDOR_ERR_GENERIC, ephemeral=True
                )

        button_now.callback = now_callback
        view.add_item(button_now)
        await interaction.response.send_message(
            content="\u200b", view=view, ephemeral=True
        )
