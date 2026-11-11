import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import content
import db
import textutil

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)
NOBLEZA_ROLE_ID = int(os.environ.get("NOBLEZA_ROLE_ID", "969477457898004481"))

COLORS = [
    ("#FF3B30", "🔴"),
    ("#FF9500", "🟠"),
    ("#FFCC00", "🟡"),
    ("#34C759", "🟢"),
    ("#00C7BE", "🟩"),
    ("#30B0C7", "🔷"),
    ("#32ADE6", "🔵"),
    ("#007AFF", "💙"),
    ("#5856D6", "🟣"),
    ("#AF52DE", "💜"),
    ("#FF2D55", "🌸"),
    ("#FF6B9A", "🌺"),
    ("#A2845E", "🟤"),
    ("#8E8E93", "⚪"),
    ("#1C1C1E", "⚫"),
    ("#90A4AE", "🌫️"),
    ("#2ECC71", "💚"),
    ("#F1C40F", "💛"),
    ("#E67E22", "🧡"),
    ("#34495E", "🌑"),
]


def parse_hex(raw: str) -> Optional[int]:
    value = raw.strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


class PreviewView(discord.ui.View):
    def __init__(self, cog: "Vestidor", user_id: int, color: int, nickname: str):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.color = color
        self.nickname = nickname
        save = discord.ui.Button(label=content.VESTIDOR_SAVE, style=discord.ButtonStyle.success)
        cancel = discord.ui.Button(label=content.VESTIDOR_CANCEL, style=discord.ButtonStyle.secondary)
        save.callback = self.save
        cancel.callback = self.cancel
        self.add_item(save)
        self.add_item(cancel)

    async def save(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        ok, error = await self.cog.apply(interaction.user, self.color, self.nickname)
        if ok:
            await interaction.message.edit(content=content.VESTIDOR_SUCCESS, embed=None, view=None)
        else:
            await interaction.message.edit(content=error, embed=None, view=None)

    async def cancel(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        await interaction.message.delete()


class NicknameModal(discord.ui.Modal):
    def __init__(self, cog: "Vestidor", color: int):
        super().__init__(title=content.VESTIDOR_NICK_TITLE, timeout=600)
        self.cog = cog
        self.color = color
        self.name_input = discord.ui.TextInput(
            label=content.VESTIDOR_NAME_LABEL,
            placeholder=content.VESTIDOR_NAME_PLACEHOLDER,
            max_length=25,
            required=True,
        )
        self.emoji_input = discord.ui.TextInput(
            label=content.VESTIDOR_EMOJIS_LABEL,
            placeholder=content.VESTIDOR_EMOJIS_PLACEHOLDER,
            max_length=16,
            required=True,
        )
        self.add_item(self.name_input)
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.finish(
            interaction,
            self.color,
            str(self.name_input.value),
            str(self.emoji_input.value),
        )


class CustomColorModal(discord.ui.Modal):
    def __init__(self, cog: "Vestidor"):
        super().__init__(title=content.VESTIDOR_CUSTOM_TITLE, timeout=600)
        self.cog = cog
        self.hex_input = discord.ui.TextInput(
            label=content.VESTIDOR_HEX_LABEL,
            placeholder=content.VESTIDOR_HEX_PLACEHOLDER,
            max_length=7,
            required=True,
        )
        self.name_input = discord.ui.TextInput(
            label=content.VESTIDOR_NAME_LABEL,
            placeholder=content.VESTIDOR_NAME_PLACEHOLDER,
            max_length=25,
            required=True,
        )
        self.emoji_input = discord.ui.TextInput(
            label=content.VESTIDOR_EMOJIS_LABEL,
            placeholder=content.VESTIDOR_EMOJIS_PLACEHOLDER,
            max_length=16,
            required=True,
        )
        self.add_item(self.hex_input)
        self.add_item(self.name_input)
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        color = parse_hex(str(self.hex_input.value))
        if color is None:
            await interaction.response.send_message(content.VESTIDOR_ERR_HEX, ephemeral=True)
            return
        await self.cog.finish(
            interaction,
            color,
            str(self.name_input.value),
            str(self.emoji_input.value),
        )


class Vestidor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def open_panel(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title=content.VESTIDOR_TITLE,
            description=content.VESTIDOR_DESCRIPTION,
            color=0x90A4AE,
        )
        options = [
            discord.SelectOption(label=hex_value, value=hex_value, emoji=emoji_char)
            for hex_value, emoji_char in COLORS
        ]
        options.append(
            discord.SelectOption(
                label=content.VESTIDOR_CUSTOM_OPTION,
                value="custom",
                emoji="🎨",
            )
        )
        select = discord.ui.Select(
            placeholder=content.VESTIDOR_SELECT_PLACEHOLDER,
            options=options,
        )
        view = discord.ui.View(timeout=300)

        async def on_select(inter: discord.Interaction) -> None:
            value = select.values[0]
            if value == "custom":
                await inter.response.send_modal(CustomColorModal(self))
            else:
                await inter.response.send_modal(
                    NicknameModal(self, int(value.lstrip("#"), 16))
                )

        select.callback = on_select
        view.add_item(select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="vestidor", description=content.CMD_VESTIDOR_DESC)
    @app_commands.guilds(GUILD_OBJ)
    async def vestidor(self, interaction: discord.Interaction) -> None:
        await self.open_panel(interaction)

    async def finish(
        self,
        interaction: discord.Interaction,
        color: int,
        name: str,
        emojis: str,
    ) -> None:
        tiny = textutil.to_tiny(name.strip())
        if not tiny:
            await interaction.response.send_message(content.VESTIDOR_ERR_GENERIC, ephemeral=True)
            return
        emo = textutil.validate_emojis(emojis)
        if emo is None:
            await interaction.response.send_message(content.VESTIDOR_ERR_EMOJIS, ephemeral=True)
            return
        nickname = f"{tiny} {emo}"
        if textutil.utf16_len(nickname) > 32:
            await interaction.response.send_message(content.VESTIDOR_ERR_LENGTH, ephemeral=True)
            return
        embed = discord.Embed(
            title=content.VESTIDOR_PREVIEW_TITLE,
            description=content.VESTIDOR_PREVIEW_DESCRIPTION.format(apodo=nickname),
            color=color,
        )
        view = PreviewView(self, interaction.user.id, color, nickname)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def apply(
        self,
        member: discord.Member,
        color: int,
        nickname: str,
    ) -> tuple[bool, Optional[str]]:
        pool = db.pool()
        if pool is None:
            return False, content.VESTIDOR_ERR_GENERIC
        guild = member.guild
        tiny_name = nickname.rsplit(" ", 1)[0]
        role_name = f"🎨 {tiny_name}"[:100]
        nobleza = guild.get_role(NOBLEZA_ROLE_ID)
        position = max(1, (nobleza.position - 1) if nobleza else 1)
        try:
            row = await pool.fetchrow(
                "SELECT role_id FROM personal_roles WHERE user_id=$1",
                member.id,
            )
            role = guild.get_role(row["role_id"]) if row else None
            if role is None:
                role = await guild.create_role(
                    name=role_name,
                    color=discord.Color(color),
                    permissions=discord.Permissions.none(),
                    hoist=False,
                    mentionable=False,
                    reason="Vestidor",
                )
            else:
                await role.edit(name=role_name, color=discord.Color(color), reason="Vestidor")
            try:
                await role.edit(position=position, reason="Vestidor")
            except discord.HTTPException:
                pass
            await member.add_roles(role, reason="Vestidor")
        except Exception:
            return False, content.VESTIDOR_ERR_GENERIC
        try:
            await pool.execute(
                "INSERT INTO personal_roles (user_id, role_id, color, nickname, updated_at) "
                "VALUES ($1,$2,$3,$4,NOW()) "
                "ON CONFLICT (user_id) DO UPDATE SET role_id=EXCLUDED.role_id, "
                "color=EXCLUDED.color, nickname=EXCLUDED.nickname, updated_at=NOW()",
                member.id,
                role.id,
                color,
                nickname,
            )
        except Exception:
            return False, content.VESTIDOR_ERR_GENERIC
        try:
            await member.edit(nick=nickname, reason="Vestidor")
            return True, None
        except discord.Forbidden:
            return False, content.VESTIDOR_ERR_OWNER.format(apodo=nickname)
        except discord.HTTPException:
            return False, content.VESTIDOR_ERR_GENERIC

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        pool = db.pool()
        if pool is None:
            return
        try:
            row = await pool.fetchrow(
                "SELECT role_id FROM personal_roles WHERE user_id=$1",
                member.id,
            )
            if row is None:
                return
            role = member.guild.get_role(row["role_id"])
            if role is not None:
                try:
                    await role.delete(reason="Vestidor: miembro salió")
                except discord.HTTPException:
                    pass
            await pool.execute(
                "DELETE FROM personal_roles WHERE user_id=$1",
                member.id,
            )
        except Exception:
            pass
