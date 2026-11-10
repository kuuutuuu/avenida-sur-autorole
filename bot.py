import asyncio
import logging
import os

import discord
from aiohttp import web

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


@client.event
async def on_ready() -> None:
    state["ready"] = True
    log.info("Conectado como %s (%s)", client.user, client.user.id)
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        log.error("El bot no esta en el guild %s", GUILD_ID)
        return
    for member in guild.members:
        if not member.bot and len(member.roles) == 0:
            await assign(member, "Catch-up: nuevo miembro sin roles")
    log.info("Catch-up completado en %s", guild.name)


@client.event
async def on_member_join(member: discord.Member) -> None:
    if member.guild.id != GUILD_ID:
        return
    await assign(member, "Autorole: nuevo miembro")


async def health(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def status(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "ready": state["ready"],
            "user": str(client.user) if client.user else None,
            "guilds": [guild.name for guild in client.guilds],
        }
    )


async def main() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/status", status)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Health endpoint en el puerto %s", PORT)
    async with client:
        await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
