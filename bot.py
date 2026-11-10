import asyncio
import logging
import os

import discord
from aiohttp import web
from discord.http import Route

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
ROLE_ID = int(os.environ["ROLE_ID"])
PORT = int(os.environ.get("PORT", "10000"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("avenida-autorole")

intents = discord.Intents.default()
intents.members = True  # Privileged: Server Members Intent

client = discord.Client(intents=intents)
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
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        log.error("El bot no esta en el guild %s", GUILD_ID)
        return
    cached = [m for m in guild.members if not m.bot and len(m.roles) == 0]
    log.info("Cache: %s miembros en guild, %s sin rol", len(guild.members), len(cached))
    try:
        members = await client.http.request(
            Route("GET", "/guilds/{guild_id}/members", guild_id=GUILD_ID),
            params={"limit": 1000},
        )
        zero = [m for m in members if not m["user"].get("bot") and len(m.get("roles", [])) == 0]
        log.info("REST: %s miembros, %s sin rol", len(members), len(zero))
        for m in zero:
            await client.http.request(
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


@client.event
async def on_ready() -> None:
    state["ready"] = True
    log.info("Conectado como %s (%s)", client.user, client.user.id)
    await catch_up()
    log.info("Catch-up completado")


@client.event
async def on_member_join(member: discord.Member) -> None:
    if member.guild.id != GUILD_ID:
        return
    await assign(member, "Autorole: nuevo miembro")


async def health(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def status(_: web.Request) -> web.Response:
    guild = client.get_guild(GUILD_ID)
    zero = [m.name for m in guild.members if not m.bot and len(m.roles) == 0] if guild else []
    return web.json_response(
        {
            "ready": state["ready"],
            "user": str(client.user) if client.user else None,
            "guilds": [g.name for g in client.guilds],
            "members_cached": len(guild.members) if guild else None,
            "zero_role_cached": zero,
        }
    )


async def debug(_: web.Request) -> web.Response:
    try:
        members = await client.http.request(
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
    async with client:
        await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
