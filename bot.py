import asyncio
import logging
import os

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from discord.http import Route

import content
import db
from encuesta import Encuesta
from excomulgar import Excomulgar
from memardo import Memardo
from ojo import Ojo
from quote import Quote, quote_context_menu
from sexo import Sexo
from vestidor import Vestidor
from welcome import Welcome

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("avenida-bot")

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
ROLE_ID = int(os.environ["ROLE_ID"])
PORT = int(os.environ.get("PORT", "10000"))
GUILD_OBJ = discord.Object(id=GUILD_ID)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("avenida-bot")

intents = discord.Intents.default()
intents.members = True  # Privileged: Server Members Intent
intents.message_content = True  # Needed for filters/quote/auto-responses later

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
state = {"ready": False, "sync_error": None, "synced": 0}


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


async def sync_commands() -> None:
    try:
        cmds = bot.tree.get_commands(guild=GUILD_OBJ)
        log.info("Comandos en el arbol: %s", [c.name for c in cmds])
        if not cmds:
            state["sync_error"] = "arbol vacio"
            return
        synced = await bot.tree.sync(guild=GUILD_OBJ)
        state["synced"] = len(synced)
        state["sync_error"] = None
        log.info("Comandos sincronizados: %s", [c.name for c in synced])
    except Exception as exc:
        state["sync_error"] = repr(exc)
        log.warning("No se pudieron sincronizar comandos: %r", exc)


@bot.event
async def on_ready() -> None:
    state["ready"] = True
    log.info("Conectado como %s (%s)", bot.user, bot.user.id)
    await catch_up()
    log.info("Catch-up completado")
    await sync_commands()


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if member.guild.id != GUILD_ID or member.bot:
        return
    await assign(member, "Autorole: nuevo miembro")


def build_help_embed() -> discord.Embed:
    lines = []
    for cmd in sorted(bot.tree.get_commands(guild=GUILD_OBJ), key=lambda c: c.name):
        if isinstance(cmd, app_commands.Command) and cmd.name not in content.HELP_HIDDEN_COMMANDS:
            lines.append(f"`/{cmd.name}` — {cmd.description}")
    description = content.HELP_DESCRIPTION.strip()
    if lines:
        description = (description + "\n\n" if description else "") + "\n".join(lines)
    embed = discord.Embed(title=content.HELP_TITLE, description=description or None, color=0x90A4AE)
    embed.set_footer(text=content.HELP_FOOTER)
    return embed


async def send_help(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(embed=build_help_embed(), ephemeral=True)


@bot.tree.command(name="ayuda", description=content.CMD_AYUDA_DESC, guild=GUILD_OBJ)
async def ayuda(interaction: discord.Interaction) -> None:
    await send_help(interaction)


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


async def commands_info(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "tree": [c.name for c in bot.tree.get_commands(guild=GUILD_OBJ)],
            "synced": state["synced"],
            "sync_error": state["sync_error"],
        }
    )


async def sync_now(_: web.Request) -> web.Response:
    await sync_commands()
    return web.json_response({"synced": state["synced"], "sync_error": state["sync_error"]})


async def memardo_test(_: web.Request) -> web.Response:
    cog = bot.get_cog("Memardo")
    if cog is None:
        return web.json_response({"ok": False, "error": "Memardo no cargado"}, status=500)
    ok, error = await cog.publish(forced=True)
    return web.json_response(
        {"ok": ok, "error": error},
        status=200 if ok else 500,
    )


async def main() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/status", status)
    app.router.add_get("/commands", commands_info)
    app.router.add_get("/sync", sync_now)
    app.router.add_get("/memardo-test", memardo_test)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Health endpoint en el puerto %s", PORT)
    await db.init()
    await bot.add_cog(Vestidor(bot))
    await bot.add_cog(Ojo(bot))
    await bot.add_cog(Welcome(bot))
    await bot.add_cog(Quote(bot))
    await bot.add_cog(Encuesta(bot))
    await bot.add_cog(Memardo(bot))
    await bot.add_cog(Sexo(bot))
    await bot.add_cog(Excomulgar(bot))
    bot.tree.add_command(quote_context_menu, guild=GUILD_OBJ)
    try:
        async with bot:
            await bot.start(TOKEN)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
