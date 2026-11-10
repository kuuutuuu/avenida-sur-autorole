import asyncio
import logging
import os

import discord
from aiohttp import web
from discord.ext import commands
from discord.http import Route

import db

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
ROLE_ID = int(os.environ["ROLE_ID"])
PORT = int(os.environ.get("PORT", "10000"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("avenida-bot")

intents = discord.Intents.default()
intents.members = True  # Privileged: Server Members Intent
intents.message_content = True  # Needed for filters/quote/auto-responses later

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
state = {"ready": False}


async def assign(member: discord.Member, reason: str) -> None:
    role = member.guild.get_role(ROLE_ID)
    if role is None or role in member.roles:
        return
    try:
        await member.add_roles(role, reason=reason)
        log.info("Rol %s asignado a %s (%s)", role.name, member, member.id)
    except discord.HTTPException as exc:
        log.warning("No se pudo asignar el rol a %s: %s", member, exc)


async def catch_up() -> None:
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        log.error("El bot no esta en el guild %s", GUILD_ID)
        return
    cached = [m for m in guild.members if not m.bot and len(m.roles) == 0]
    log.info("Cache: %s miembros en guild, %s sin rol", len(guild.members), len(cached))
    try:
        members = await bot.http.request(
            Route("GET", "/guilds/{guild_id}/members", guild_id=GUILD_ID),
            params={"limit": 1000},
        )
        zero = [m for m in members if not m["user"].get("bot") and len(m.get("roles", [])) == 0]
        log.info("REST: %s miembros, %s sin rol", len(members), len(zero))
        for m in zero:
            await bot.http.request(
                Route(
                    "PUT",
                    "/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
                    guild_id=GUILD_ID,
                    user_id=m["user"]["id"],
                    role_id=ROLE_ID,
                ),
                reason="Catch-up autorole Forastero",
            )
            log.info("Rol Forastero asignado (REST) a %s", m["user"]["username"])
    except Exception as exc:
        log.warning("Catch-up REST fallo (%s), usando cache", exc)
        for member in cached:
            await assign(member, "Catch-up autorole Forastero (cache)")


@bot.event
async def on_ready() -> None:
    state["ready"] = True
    log.info("Conectado como %s (%s)", bot.user, bot.user.id)
    await catch_up()
    log.info("Catch-up completado")
    # Sync de comandos solo cuando existan (fases siguientes)
    try:
        if bot.tree.get_commands():
            await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            log.info("Comandos sincronizados en el guild")
    except Exception as exc:
        log.warning("No se pudieron sincronizar comandos: %s", exc)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if member.guild.id != GUILD_ID or member.bot:
        return
    await assign(member, "Autorole: nuevo miembro")


async def health(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def status(_: web.Request) -> web.Response:
    guild = bot.get_guild(GUILD_ID)
    zero = [m.name for m in guild.members if not m.bot and len(m.roles) == 0] if guild else []
    return web.json_response(
        {
            "ready": state["ready"],
            "user": str(bot.user) if bot.user else None,
            "guilds": [g.name for g in bot.guilds],
            "members_cached": len(guild.members) if guild else None,
            "zero_role_cached": zero,
            "db": db.pool() is not None,
        }
    )


async def debug(_: web.Request) -> web.Response:
    try:
        members = await bot.http.request(
            Route("GET", "/guilds/{guild_id}/members", guild_id=GUILD_ID),
            params={"limit": 1000},
        )
        return web.json_response(
            {
                "total": len(members),
                "zero_role": [
                    m["user"]["username"]
                    for m in members
                    if not m["user"].get("bot") and len(m.get("roles", [])) == 0
                ],
            }
        )
    except Exception as exc:
        return web.json_response({"error": str(exc)}, status=500)


async def main() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/status", status)
    app.router.add_get("/debug", debug)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Health endpoint en el puerto %s", PORT)
    await db.init()
    try:
        async with bot:
            await bot.start(TOKEN)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
