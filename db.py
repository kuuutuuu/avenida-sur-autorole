import logging
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

log = logging.getLogger("avenida-db")


def _sanitize(url: str) -> str:
    """Neon agrega channel_binding; asyncpg no lo entiende, lo quitamos."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(query)))

SCHEMA = """
CREATE TABLE IF NOT EXISTS personal_roles (
    user_id BIGINT PRIMARY KEY,
    role_id BIGINT NOT NULL,
    color INTEGER NOT NULL,
    nickname TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verifications (
    user_id BIGINT PRIMARY KEY,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS polls (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT,
    channel_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    options JSONB NOT NULL,
    closed BOOLEAN NOT NULL DEFAULT FALSE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS poll_votes (
    poll_id BIGINT NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    option_index INTEGER NOT NULL,
    PRIMARY KEY (poll_id, user_id)
);

CREATE TABLE IF NOT EXISTS birthdays (
    user_id BIGINT PRIMARY KEY,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    year INTEGER,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS excomulgar_usage (
    user_id BIGINT NOT NULL,
    used_on DATE NOT NULL,
    PRIMARY KEY (user_id, used_on)
);

CREATE TABLE IF NOT EXISTS daily_memes (
    meme_date DATE PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    url TEXT,
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_pool = None


async def init() -> None:
    global _pool
    url = os.environ.get("DATABASE_URL")
    if not url:
        log.info("DATABASE_URL no configurada; DB deshabilitada")
        return
    try:
        _pool = await asyncpg.create_pool(
            dsn=_sanitize(url),
            min_size=1,
            max_size=5,
            command_timeout=20,
        )
        async with _pool.acquire() as conn:
            await conn.execute(SCHEMA)
        log.info("Neon conectado y esquema asegurado")
    except Exception as exc:
        log.error("No se pudo conectar a Neon: %s", exc)
        _pool = None


def pool():
    return _pool


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
