import io
import os
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import content

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)
OWNER_ID = int(os.environ.get("OWNER_ID", "310866269299671052"))
NOBLEZA_ROLE_ID = int(os.environ.get("NOBLEZA_ROLE_ID", "969477457898004481"))
PROXY_URL = os.environ.get("CUANTOCABRON_PROXY_URL", "").rstrip("/")
PROXY_FALLBACK_URL = os.environ.get("CUANTOCABRON_PROXY_FALLBACK_URL", "").rstrip("/")
PROXY_TOKEN = os.environ.get("CUANTOCABRON_PROXY_TOKEN", "")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def image_extension(url: str, content_type: str) -> str:
    content_type = (content_type or "").lower()
    if "gif" in content_type:
        return ".gif"
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    clean = url.lower().split("?")[0]
    for extension in (".gif", ".png", ".webp", ".jpg", ".jpeg"):
        if clean.endswith(extension):
            return ".jpg" if extension == ".jpeg" else extension
    return ".png"


async def fetch_cuantocabron(session: aiohttp.ClientSession):
    if not PROXY_TOKEN:
        raise RuntimeError("proxy sin token")
    bases = [
        base for base in (PROXY_URL, PROXY_FALLBACK_URL) if base
    ]
    if not bases:
        raise RuntimeError("proxy no configurado")
    last_error = None
    for base in bases:
        try:
            async with session.get(
                f"{base}/cc",
                params={"token": PROXY_TOKEN},
                timeout=60,
            ) as response:
                response.raise_for_status()
                data = await response.json()
            if not data.get("ok"):
                raise RuntimeError(
                    data.get("error") or "CuantoCabron sin imagen"
                )
            image_url = data["image"]
            async with session.get(
                f"{base}/img",
                params={"token": PROXY_TOKEN, "url": image_url},
                timeout=60,
            ) as response:
                response.raise_for_status()
                image = await response.read()
                content_type = response.headers.get(
                    "Content-Type", "image/jpeg"
                )
            if len(image) > MAX_IMAGE_BYTES:
                raise RuntimeError("imagen demasiado grande")
            return (
                data.get("title", ""),
                data.get("url", ""),
                image,
                image_extension(image_url, content_type),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(str(last_error) if last_error else "sin imagen")


async def fetch_reddit(session: aiohttp.ClientSession):
    if not PROXY_TOKEN:
        raise RuntimeError("proxy sin token")
    bases = [base for base in (PROXY_URL, PROXY_FALLBACK_URL) if base]
    if not bases:
        raise RuntimeError("proxy no configurado")
    last_error = None
    for base in bases:
        try:
            async with session.get(
                f"{base}/reddit",
                params={"token": PROXY_TOKEN},
                timeout=60,
            ) as response:
                response.raise_for_status()
                data = await response.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error") or "Reddit sin imagen")
            for candidate in (data.get("image"), data.get("image_fallback")):
                if not candidate:
                    continue
                try:
                    async with session.get(
                        f"{base}/img",
                        params={"token": PROXY_TOKEN, "url": candidate},
                        timeout=60,
                    ) as response:
                        response.raise_for_status()
                        image = await response.read()
                        content_type = response.headers.get(
                            "Content-Type", ""
                        )
                    if not content_type.startswith("image/"):
                        raise RuntimeError("no es imagen")
                    if len(image) > MAX_IMAGE_BYTES:
                        raise RuntimeError("imagen demasiado grande")
                    return (
                        data.get("title", ""),
                        data.get("url", ""),
                        image,
                        image_extension(candidate, content_type),
                    )
                except Exception as exc:
                    last_error = exc
                    continue
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(str(last_error) if last_error else "sin imagen")


class Memardo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="memardodeldia",
        description=content.MEMARDODIA_CMD_DESC,
    )
    @app_commands.guilds(GUILD_OBJ)
    @app_commands.describe(fuente=content.MEMARDODIA_SOURCE_DESC)
    @app_commands.choices(
        fuente=[
            app_commands.Choice(
                name=content.MEMARDO_SOURCE_CC, value="cuantocabron"
            ),
            app_commands.Choice(
                name=content.MEMARDO_SOURCE_REDDIT, value="reddit"
            ),
        ]
    )
    async def memardodeldia(
        self,
        interaction: discord.Interaction,
        fuente: app_commands.Choice[str],
    ) -> None:
        roles = getattr(interaction.user, "roles", [])
        es_nobleza = interaction.user.id == OWNER_ID or any(
            role.id == NOBLEZA_ROLE_ID for role in roles
        )
        if not es_nobleza:
            await interaction.response.send_message(
                content.MEMARDODIA_NOT_NOBLEZA, ephemeral=True
            )
            return
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                if fuente.value == "reddit":
                    title, page_url, image, extension = await fetch_reddit(
                        session
                    )
                else:
                    title, page_url, image, extension = await fetch_cuantocabron(
                        session
                    )
            filename = f"meme{extension}"
            embed = discord.Embed(
                title=content.MEMARDO_TITLE,
                description=title[:200] if title else None,
                url=page_url,
                color=0x90A4AE,
            )
            embed.set_image(url=f"attachment://{filename}")
            await interaction.followup.send(
                embed=embed,
                file=discord.File(io.BytesIO(image), filename=filename),
            )
        except Exception:
            await interaction.followup.send(
                content.MEMARDODIA_ERROR, ephemeral=True
            )
