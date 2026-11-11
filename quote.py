import io
import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji

import content

BASE = Path(__file__).parent
FONT_SANS = BASE / "assets" / "fonts" / "DejaVuSans-Bold.ttf"
FONT_SERIF = BASE / "assets" / "fonts" / "DejaVuSerif-Bold.ttf"

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)

MAX_QUOTE_CHARS = 280


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def generate_quote(
    avatar_bytes: bytes,
    name: str,
    quote_text: str,
    created_year: int,
    current_year: int,
) -> bytes:
    width, height = 900, 450
    img = Image.new("RGB", (width, height), "#0A0A0A")
    draw = ImageDraw.Draw(img)
    draw.rectangle([14, 14, width - 14, height - 14], outline="#FFFFFF", width=2)

    # avatar en gris, circular
    size = 240
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("L").resize(
        (size, size), Image.LANCZOS
    )
    avatar_rgb = Image.merge("RGB", (avatar, avatar, avatar))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    ax, ay = 50, 105
    img.paste(avatar_rgb, (ax, ay), mask)
    draw.ellipse(
        [ax - 3, ay - 3, ax + size + 3, ay + size + 3],
        outline="#FFFFFF",
        width=3,
    )

    # quote entre comillas, ajustada al ancho
    text = f'"{quote_text.strip()}"'
    max_w = 470
    font_size = 38
    lines = []
    font = _font(FONT_SERIF, font_size)
    while font_size > 18:
        font = _font(FONT_SERIF, font_size)
        lines = []
        current = ""
        for word in text.split():
            candidate = (current + " " + word).strip()
            if draw.textlength(candidate, font=font) <= max_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= 6:
            break
        font_size -= 2

    pilmoji = Pilmoji(img)
    y = 55
    for line in lines:
        pilmoji.text((330, y), line, font=font, fill="#FFFFFF")
        y += int(font_size * 1.3)

    # apodo y, debajo a la derecha, el rango de años de la cuenta
    name_text = f"— {name}"
    name_font = _font(FONT_SANS, 24)
    while name_font.getlength(name_text) > 470 and name_font.size > 14:
        name_font = _font(FONT_SANS, name_font.size - 2)
    name_y = min(y + 18, height - 80)
    pilmoji.text((330, name_y), name_text, font=name_font, fill="#BDBDBD")

    date_text = f"({created_year}-{current_year})"
    date_font = _font(FONT_SANS, 20)
    date_width = date_font.getlength(date_text)
    name_width = name_font.getlength(name_text)
    date_x = max(330, min(330 + name_width - date_width, 330 + 470 - date_width))
    pilmoji.text(
        (date_x, name_y + name_font.size + 4),
        date_text,
        font=date_font,
        fill="#8E8E93",
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class Quote(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="quote", description=content.QUOTE_CMD_DESC)
    @app_commands.guilds(GUILD_OBJ)
    @app_commands.describe(
        texto=content.QUOTE_TEXT_DESC,
        autor=content.QUOTE_AUTHOR_DESC,
    )
    async def quote(
        self,
        interaction: discord.Interaction,
        texto: str,
        autor: discord.Member | None = None,
    ) -> None:
        author = autor or interaction.user
        await self.send_quote(interaction, author, texto)

    async def handle_context(
        self,
        interaction: discord.Interaction,
        message: discord.Message,
    ) -> None:
        text = (message.content or "").strip()
        if not text:
            await interaction.response.send_message(
                content.QUOTE_EMPTY_ERROR, ephemeral=True
            )
            return
        member = message.guild.get_member(message.author.id) if message.guild else None
        author = member or message.author
        await self.send_quote(interaction, author, text)

    async def send_quote(
        self,
        interaction: discord.Interaction,
        author: discord.abc.User,
        text: str,
    ) -> None:
        try:
            text = text.strip()
            if len(text) > MAX_QUOTE_CHARS:
                text = text[: MAX_QUOTE_CHARS - 3] + "..."
            avatar = await author.display_avatar.read()
            created_year = discord.utils.snowflake_time(author.id).year
            current_year = datetime.now(timezone.utc).year
            png = generate_quote(
                avatar,
                author.display_name,
                text,
                created_year,
                current_year,
            )
            await interaction.response.send_message(
                file=discord.File(io.BytesIO(png), filename="quote.png")
            )
        except Exception:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    content.QUOTE_GENERIC_ERROR, ephemeral=True
                )


@app_commands.context_menu(name=content.QUOTE_CONTEXT_NAME)
async def quote_context_menu(
    interaction: discord.Interaction,
    message: discord.Message,
) -> None:
    cog = interaction.client.get_cog("Quote")
    if cog is None:
        await interaction.response.send_message(
            content.QUOTE_GENERIC_ERROR, ephemeral=True
        )
        return
    await cog.handle_context(interaction, message)
