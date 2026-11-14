import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

import content
import db

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)
OWNER_ID = int(os.environ.get("OWNER_ID", "310866269299671052"))
NOBLEZA_ROLE_ID = int(os.environ.get("NOBLEZA_ROLE_ID", "969477457898004481"))
TZ = ZoneInfo("America/Caracas")


class Excomulgar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="excomulgar", description=content.EXCOM_CMD_DESC)
    @app_commands.guilds(GUILD_OBJ)
    @app_commands.describe(usuario=content.EXCOM_USER_DESC)
    async def excomulgar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
    ) -> None:
        roles = getattr(interaction.user, "roles", [])
        es_nobleza = interaction.user.id == OWNER_ID or any(
            role.id == NOBLEZA_ROLE_ID for role in roles
        )
        if not es_nobleza:
            await interaction.response.send_message(
                content.EXCOM_NOT_NOBLEZA, ephemeral=True
            )
            return
        if (
            usuario.bot
            or usuario.id == OWNER_ID
            or usuario.id == interaction.user.id
        ):
            await interaction.response.send_message(
                content.EXCOM_BAD_TARGET, ephemeral=True
            )
            return
        pool = db.pool()
        if pool is None:
            await interaction.response.send_message(
                content.VESTIDOR_ERR_GENERIC, ephemeral=True
            )
            return
        today = datetime.now(TZ).date()
        try:
            used = await pool.fetchval(
                "SELECT 1 FROM excomulgar_usage "
                "WHERE user_id=$1 AND used_on=$2",
                interaction.user.id,
                today,
            )
        except Exception:
            used = None
        if used:
            await interaction.response.send_message(
                content.EXCOM_ALREADY_USED, ephemeral=True
            )
            return
        try:
            await usuario.timeout(
                discord.utils.utcnow() + timedelta(seconds=60),
                reason=content.EXCOM_TITLE,
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                content.EXCOM_BAD_TARGET, ephemeral=True
            )
            return
        try:
            await pool.execute(
                "INSERT INTO excomulgar_usage (user_id, used_on) "
                "VALUES ($1,$2) ON CONFLICT DO NOTHING",
                interaction.user.id,
                today,
            )
        except Exception:
            pass
        embed = discord.Embed(
            title=content.EXCOM_TITLE,
            description=content.EXCOM_TEXT.format(usuario=usuario.mention),
            color=0xE74C3C,
        )
        await interaction.response.send_message(embed=embed)
