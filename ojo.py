import os
import re
from collections import defaultdict, deque
from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands

import content
import db

GUILD_ID = int(os.environ["GUILD_ID"])
FORASTERO_ROLE_ID = int(os.environ["ROLE_ID"])
OWNER_ID = int(os.environ.get("OWNER_ID", "310866269299671052"))
INFO_CATEGORY_ID = 969498559340740648  # 📄 Información / Comandos 📄

BURST_MAX = 5  # mensajes
BURST_WINDOW = 5  # segundos
DUP_MAX = 3  # mensajes identicos
DUP_WINDOW = 30  # segundos
MENTION_MAX = 5
AGE_DAYS = 7
BURST_TIMEOUT_MIN = 5
DUP_TIMEOUT_MIN = 10
MENTION_TIMEOUT_MIN = 5
INVITE_TIMEOUT_MIN = 10
PHISH_TIMEOUT_MIN = 30

INVITE_RE = re.compile(r"(discord\.gg/|discord(app)?\.com/invite/)", re.IGNORECASE)
PHISH_DOMAINS = {
    "discord-gift.com", "discordn.gift", "discord-airdrop.com", "discord-nitro.xyz",
    "dlscord.com", "discorde.com", "steamcommunlty.com", "steamgifts.click",
    "free-nitro.xyz", "nitro-drop.com", "disord-gift.com", "discord-giveaway.com",
    "dlscord-app.com", "discord-nitrogift.com",
}
PHISH_RE = re.compile(
    r"(discord[\-.]?(gift|nitro|airdrop|giveaway|boost)|free[\-._ ]?nitro|steam[\-._ ]?gift)",
    re.IGNORECASE,
)


class Ojo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel: Optional[discord.TextChannel] = None
        self.timestamps = defaultdict(lambda: deque(maxlen=100))
        self.contents = defaultdict(lambda: deque(maxlen=100))

    # ---------- canal de logs ----------

    async def ensure_channel(self) -> None:
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return
        pool = db.pool()
        saved = None
        if pool is not None:
            try:
                saved = await pool.fetchval(
                    "SELECT value FROM settings WHERE key='log_channel'"
                )
            except Exception:
                saved = None
        channel = guild.get_channel(int(saved)) if saved and saved.isdigit() else None
        if channel is None:
            channel = discord.utils.get(guild.text_channels, name=content.OJO_CHANNEL)
        if channel is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    embed_links=True,
                    read_message_history=True,
                ),
            }
            channel = await guild.create_text_channel(
                name=content.OJO_CHANNEL,
                overwrites=overwrites,
                reason="Ojo de Pollita",
            )
            try:
                category = guild.get_channel(INFO_CATEGORY_ID)
                if category is not None:
                    await channel.edit(category=category)
            except discord.HTTPException:
                pass
        self.log_channel = channel
        if pool is not None:
            try:
                await pool.execute(
                    "INSERT INTO settings (key, value) VALUES ('log_channel', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                    str(channel.id),
                )
            except Exception:
                pass

    async def log(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        fields: Optional[list] = None,
        color: int = 0x90A4AE,
    ) -> None:
        if self.log_channel is None:
            return
        embed = discord.Embed(title=title, description=description, color=color)
        for name, value, inline in fields or []:
            embed.add_field(name=name, value=value, inline=inline)
        embed.set_footer(text=content.HELP_FOOTER)
        try:
            await self.log_channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def timeout_and_log(
        self,
        message: discord.Message,
        reason: str,
        minutes: int,
        title: str,
    ) -> None:
        try:
            await message.author.timeout(
                discord.utils.utcnow() + timedelta(minutes=minutes),
                reason=reason,
            )
        except discord.HTTPException:
            pass
        await self.log(
            title=title,
            fields=[
                (content.OJO_F_AUTOR, f"{message.author} (`{message.author.id}`)", True),
                (content.OJO_F_CANAL, message.channel.mention, True),
                (
                    content.OJO_F_CONTENIDO,
                    (message.content or "(sin contenido)")[:500],
                    False,
                ),
            ],
            color=0xE67E22,
        )

    # ---------- eventos de log ----------

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.ensure_channel()

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        if message.author.bot:
            return
        if self.log_channel is not None and message.channel.id == self.log_channel.id:
            return
        await self.log(
            title=content.OJO_T_DELETE,
            fields=[
                (content.OJO_F_AUTOR, f"{message.author} (`{message.author.id}`)", True),
                (content.OJO_F_CANAL, message.channel.mention, True),
                (
                    content.OJO_F_CONTENIDO,
                    (message.content or "(sin contenido)")[:1000],
                    False,
                ),
            ],
            color=0xE74C3C,
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.guild.id != GUILD_ID:
            return
        if before.author.bot:
            return
        if before.content == after.content:
            return
        await self.log(
            title=content.OJO_T_EDIT,
            fields=[
                (content.OJO_F_AUTOR, f"{before.author} (`{before.author.id}`)", True),
                (content.OJO_F_CANAL, before.channel.mention, True),
                (content.OJO_F_ANTES, (before.content or "(sin contenido)")[:500], True),
                (content.OJO_F_DESPUES, (after.content or "(sin contenido)")[:500], True),
            ],
            color=0x95A5A6,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        age_days = (discord.utils.utcnow() - member.created_at).days
        fields = [
            (content.OJO_F_AUTOR, f"{member} (`{member.id}`)", True),
            (content.OJO_F_EDAD, f"{age_days} días", True),
        ]
        if member.bot:
            fields.append((content.OJO_F_MOTIVO, "Bot", True))
            await self.log(title=content.OJO_T_JOIN, fields=fields, color=0x95A5A6)
        elif age_days < AGE_DAYS:
            fields.append((content.OJO_F_MOTIVO, content.OJO_SUSPECT_MOTIVE, True))
            await self.log(title=content.OJO_T_JOIN, fields=fields, color=0xE67E22)
        else:
            await self.log(title=content.OJO_T_JOIN, fields=fields, color=0x2ECC71)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        await self.log(
            title=content.OJO_T_LEAVE,
            fields=[(content.OJO_F_AUTOR, f"{member} (`{member.id}`)", True)],
            color=0x95A5A6,
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.guild.id != GUILD_ID:
            return
        if before.nick != after.nick:
            await self.log(
                title=content.OJO_T_NICK,
                fields=[
                    (content.OJO_F_AUTOR, f"{after} (`{after.id}`)", True),
                    (content.OJO_F_ANTES, before.nick or "(sin apodo)", True),
                    (content.OJO_F_DESPUES, after.nick or "(sin apodo)", True),
                ],
                color=0x95A5A6,
            )
        if before.roles != after.roles:
            added = [r.name for r in after.roles if r not in before.roles]
            removed = [r.name for r in before.roles if r not in after.roles]
            if added or removed:
                await self.log(
                    title=content.OJO_T_ROLES,
                    fields=[
                        (content.OJO_F_AUTOR, f"{after} (`{after.id}`)", True),
                        (content.OJO_F_ANTES, ", ".join(removed) or "—", True),
                        (content.OJO_F_DESPUES, ", ".join(added) or "—", True),
                    ],
                    color=0x95A5A6,
                )
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until is not None:
                until = after.timed_out_until.strftime("%Y-%m-%d %H:%M UTC")
                await self.log(
                    title=content.OJO_T_TIMEOUT,
                    fields=[
                        (content.OJO_F_AUTOR, f"{after} (`{after.id}`)", True),
                        (content.OJO_F_DESPUES, until, True),
                    ],
                    color=0xE74C3C,
                )

    # ---------- moderacion de Forasteros ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        if message.author.bot or message.author.id == OWNER_ID:
            return
        if not isinstance(message.author, discord.Member):
            return
        if discord.utils.get(message.author.roles, id=FORASTERO_ROLE_ID) is None:
            return
        if self.log_channel is not None and message.channel.id == self.log_channel.id:
            return

        # phishing e invites
        text = message.content or ""
        if INVITE_RE.search(text):
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            await self.timeout_and_log(
                message,
                content.OJO_REASON_INVITE,
                INVITE_TIMEOUT_MIN,
                content.OJO_T_INVITE,
            )
            return
        lowered = text.lower()
        if PHISH_RE.search(text) or any(d in lowered for d in PHISH_DOMAINS):
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            await self.timeout_and_log(
                message,
                content.OJO_REASON_PHISH,
                PHISH_TIMEOUT_MIN,
                content.OJO_T_PHISH,
            )
            return

        await self.check_antispam(message)

    async def check_antispam(self, message: discord.Message) -> None:
        now = message.created_at.timestamp()
        uid = message.author.id

        stamps = self.timestamps[uid]
        stamps.append(now)
        while stamps and now - stamps[0] > BURST_WINDOW:
            stamps.popleft()
        if len(stamps) > BURST_MAX:
            self.timestamps[uid].clear()
            try:
                await message.channel.purge(
                    limit=20,
                    check=lambda m: m.author.id == uid and not m.author.bot,
                )
            except discord.HTTPException:
                pass
            await self.timeout_and_log(
                message,
                content.OJO_REASON_BURST,
                BURST_TIMEOUT_MIN,
                content.OJO_T_BURST,
            )
            return

        entries = self.contents[uid]
        entries.append((message.content or "", now))
        while entries and now - entries[0][1] > DUP_WINDOW:
            entries.popleft()
        text = message.content or ""
        if text and sum(1 for e in entries if e[0] == text) >= DUP_MAX:
            self.contents[uid].clear()
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            await self.timeout_and_log(
                message,
                content.OJO_REASON_DUPS,
                DUP_TIMEOUT_MIN,
                content.OJO_T_DUPS,
            )
            return

        if len(message.mentions) > MENTION_MAX:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            await self.timeout_and_log(
                message,
                content.OJO_REASON_MENTIONS,
                MENTION_TIMEOUT_MIN,
                content.OJO_T_MENTIONS,
            )
