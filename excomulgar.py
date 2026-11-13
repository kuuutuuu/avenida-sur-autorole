import os
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

import content

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)
OWNER_ID = int(os.environ.get("OWNER_ID", "310866269299671052"))


class Excomulgar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="excomulgar", description=content.EXCOM_CMD_DESC)
    @app_commands.guilds(GUILD_OBJ)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(usuario=content.EXCOM_USER_DESC)
    async def excomulgar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
    ) -> None:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                content.EXCOM_NOT_OWNER, ephemeral=True
            )
            return
        if usuario.bot or usuario.id == OWNER_ID:
            await interaction.response.send_message(
                content.EXCOM_BAD_TARGET, ephemeral=True
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
        embed = discord.Embed(
            title=content.EXCOM_TITLE,
            description=content.EXCOM_TEXT.format(usuario=usuario.mention),
            color=0xE74C3C,
        )
        await interaction.response.send_message(embed=embed)
