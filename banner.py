import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji

BASE = Path(__file__).parent
BG_PATH = BASE / "assets" / "welcome_bg.jpg"
FONT_PATH = BASE / "assets" / "fonts" / "DejaVuSans-Bold.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def generate_welcome_banner(name: str, avatar_bytes: bytes | None = None) -> bytes:
    """Banner de bienvenida: fondo Hobbiton + BIENVENID@ + apodo + avatar."""
    base = Image.open(BG_PATH).convert("RGB")
    target_w = 1600
    ratio = target_w / base.width
    img = base.resize((target_w, int(base.height * ratio)), Image.LANCZOS)

    title = "BIENVENID@"
    title_size = 96
    title_font = _font(title_size)
    while title_font.getlength(title) > 600 and title_size > 40:
        title_size -= 4
        title_font = _font(title_size)

    name_size = 56
    name_font = _font(name_size)
    while name_font.getlength(name) > 600 and name_size > 24:
        name_size -= 2
        name_font = _font(name_size)

    x, y = 90, 80
    pilmoji = Pilmoji(img)
    pilmoji.text(
        (x, y),
        title,
        font=title_font,
        fill="#FFFFFF",
        stroke_width=5,
        stroke_fill="#0B2A4A",
    )
    pilmoji.text(
        (x, y + title_size + 24),
        name,
        font=name_font,
        fill="#FFFFFF",
        stroke_width=4,
        stroke_fill="#0B2A4A",
    )

    if avatar_bytes:
        size = 220
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize(
            (size, size), Image.LANCZOS
        )
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        ax, ay = 860, 80
        img.paste(avatar, (ax, ay), mask)
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            [ax - 4, ay - 4, ax + size + 4, ay + size + 4],
            outline="#FFFFFF",
            width=5,
        )
        draw.ellipse(
            [ax - 8, ay - 8, ax + size + 8, ay + size + 8],
            outline="#0B2A4A",
            width=2,
        )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
