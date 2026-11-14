import io
import random
from pathlib import Path

import emoji as emoji_lib
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pilmoji import Pilmoji

import content

BASE = Path(__file__).parent
FONT_DISPLAY = BASE / "assets" / "fonts" / "LilitaOne-Regular.ttf"
FONT_NAME = BASE / "assets" / "fonts" / "DejaVuSans-Bold.ttf"


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _normalize_emoji(text: str) -> str:
    """Añade el selector de presentación a emojis que lo necesitan.

    Algunos nicks traen emojis "minimally qualified" (por ejemplo ``🏝``
    sin ``\\ufe0f``). Pilmoji solo reconoce los fully qualified, así que
    sin esto el emoji se dibuja como un cuadro vacío.
    """
    chars = list(text)
    normalized = []
    for index, char in enumerate(chars):
        if char == "\ufe0f":
            normalized.append(char)
            continue
        if index + 1 < len(chars) and chars[index + 1] == "\ufe0f":
            normalized.append(char)
            continue
        data = emoji_lib.EMOJI_DATA.get(char)
        if data and data.get("status") in (
            emoji_lib.STATUS["minimally_qualified"],
            emoji_lib.STATUS["unqualified"],
        ):
            candidate = char + "\ufe0f"
            candidate_data = emoji_lib.EMOJI_DATA.get(candidate)
            if (
                candidate_data
                and candidate_data.get("status")
                == emoji_lib.STATUS["fully_qualified"]
            ):
                normalized.append(candidate)
                continue
        normalized.append(char)
    return "".join(normalized)


def _text_size(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    probe = Image.new("RGBA", (1, 1))
    with Pilmoji(probe) as pilmoji:
        width, height = pilmoji.getsize(text, font=font)
    return int(width), int(height)


def _text_layer(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> tuple[Image.Image, int]:
    """Renderiza el texto (con emojis) una sola vez en una capa aparte."""
    width, height = _text_size(text, font)
    padding = max(12, font.size // 2)
    layer = Image.new(
        "RGBA",
        (width + padding * 2, height + padding * 2),
        (0, 0, 0, 0),
    )
    with Pilmoji(layer) as pilmoji:
        pilmoji.text(
            (padding, padding),
            text,
            font=font,
            fill=fill,
        )
    return layer, padding


def _paste_text(
    img: Image.Image,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    shadow: bool = True,
) -> None:
    """Pega el texto con una sombra suave sin duplicar los emojis."""
    layer, padding = _text_layer(text, font, fill)
    x, y = position
    if shadow:
        alpha = layer.getchannel("A").point(lambda value: int(value * 0.5))
        shadow_layer = Image.new("RGBA", layer.size, (8, 10, 14, 255))
        shadow_layer.putalpha(alpha)
        img.alpha_composite(
            shadow_layer,
            (x - padding + 3, y - padding + 4),
        )
    img.alpha_composite(layer, (x - padding, y - padding))


def generate_birthday_banner(avatar_bytes: bytes, name: str) -> bytes:
    width, height = 1000, 500
    img = Image.new("RGBA", (width, height), (14, 16, 23, 255))
    draw = ImageDraw.Draw(img)

    # degradado vertical suave
    for y in range(height):
        t = y / height
        draw.line(
            [(0, y), (width, y)],
            fill=(int(14 + 7 * t), int(16 + 9 * t), int(23 + 14 * t), 255),
        )

    # textura: rayas diagonales a baja opacidad
    texture = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    texture_draw = ImageDraw.Draw(texture)
    step = 46
    for x in range(-height, width + height, step):
        texture_draw.line(
            [(x, 0), (x + height, height)],
            fill=(255, 255, 255, 7),
            width=1,
        )
    img = Image.alpha_composite(img, texture)

    # confeti variado
    confetti = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    confetti_draw = ImageDraw.Draw(confetti)
    rng = random.Random(7)
    palette = [
        (255, 209, 102),
        (239, 71, 111),
        (6, 214, 160),
        (17, 138, 178),
        (247, 140, 107),
        (155, 93, 229),
        (255, 255, 255),
    ]
    for _ in range(95):
        x = rng.randint(0, width - 14)
        y = rng.randint(0, height - 16)
        size = rng.randint(3, 9)
        color = rng.choice(palette)
        alpha = rng.randint(60, 115)
        if rng.random() < 0.55:
            confetti_draw.ellipse(
                [x, y, x + size, y + size],
                fill=color + (alpha,),
            )
        else:
            confetti_draw.rectangle(
                [x, y, x + size, y + int(size * 1.7)],
                fill=color + (alpha,),
            )
    img = Image.alpha_composite(img, confetti)

    # resplandor dorado suave detrás del avatar
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [50, 100, 350, 400],
        fill=(255, 209, 102, 34),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img, glow)

    # sombra del avatar
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [96, 146, 324, 374],
        fill=(0, 0, 0, 95),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img = Image.alpha_composite(img, shadow)

    # avatar circular con doble aro
    avatar_size = 240
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize(
        (avatar_size, avatar_size), Image.LANCZOS
    )
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse(
        (0, 0, avatar_size, avatar_size), fill=255
    )
    img.paste(avatar, (80, 130), mask)
    draw = ImageDraw.Draw(img)
    draw.ellipse([76, 126, 324, 374], outline=(255, 209, 102, 255), width=6)
    draw.ellipse([85, 135, 315, 365], outline=(255, 255, 255, 255), width=2)

    # titulo en dos lineas
    title_parts = content.BIRTHDAY_TITLE.split(" ")
    title_size = 74
    title_font = _font(FONT_DISPLAY, title_size)
    title_width = max(_text_size(part, title_font)[0] for part in title_parts)
    while title_width > 540 and title_size > 40:
        title_size -= 2
        title_font = _font(FONT_DISPLAY, title_size)
        title_width = max(
            _text_size(part, title_font)[0] for part in title_parts
        )
    x = 380
    title_y = 92
    line_height = int(title_size * 1.02)
    for index, part in enumerate(title_parts):
        _paste_text(
            img,
            (x, title_y + index * line_height),
            part,
            title_font,
            "#FFD166",
        )

    # divisor dorado
    divider_y = title_y + len(title_parts) * line_height + 12
    draw.rectangle(
        [x, divider_y, x + title_width, divider_y + 4],
        fill=(255, 209, 102, 255),
    )

    # nombre
    name = _normalize_emoji(name)
    name_size = 34
    name_font = _font(FONT_NAME, name_size)
    while _text_size(name, name_font)[0] > 540 and name_size > 18:
        name_size -= 2
        name_font = _font(FONT_NAME, name_size)
    _paste_text(
        img,
        (x, divider_y + 22),
        name,
        name_font,
        "#FFFFFF",
        shadow=False,
    )

    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()
