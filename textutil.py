import unicodedata

import emoji

# Tiny caps: minusculas estilizadas. Q no tiene small-cap estandar; usamos
# U+A7AF (LATIN LETTER SMALL CAPITAL Q). Ñ se conserva en mayuscula.
TINY = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ", "g": "ɢ",
    "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ",
    "o": "ᴏ", "p": "ᴘ", "q": "ꞯ", "r": "ʀ", "s": "ꜱ", "t": "ᴛ", "u": "ᴜ",
    "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
}


def to_tiny(text: str) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low == "ñ":
            out.append("Ñ")
            continue
        base = unicodedata.normalize("NFKD", low)
        base = "".join(c for c in base if not unicodedata.combining(c))
        if len(base) == 1 and base in TINY:
            out.append(TINY[base])
        else:
            out.append(ch)
    return "".join(out)


def validate_emojis(raw: str) -> str | None:
    compact = "".join(raw.split())
    if not compact:
        return None
    matches = emoji.emoji_list(compact)
    if len(matches) != 2:
        return None
    if "".join(m["emoji"] for m in matches) != compact:
        return None
    return compact


def utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2
