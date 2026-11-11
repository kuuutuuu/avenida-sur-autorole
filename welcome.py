import io
import os

import discord
from discord.ext import commands

import banner
import content
import db

GUILD_ID = int(os.environ["GUILD_ID"])
ISLA_CHANNEL_ID = 1569496544598565015
RULES_CHANNEL_ID = 1569497653664944151


class OptionsView(discord.ui.View):
    def __init__(self, cog: "Welcome"):
        super().__init__(timeout=600)
        self.cog = cog
        self.add_item(
            discord.ui.Button(
                label=content.WELCOME_OPT_RULES,
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{GUILD_ID}/{RULES_CHANNEL_ID}",
            )
        )
        self.add_item(
            discord.ui.Button(
                label=content.WELCOME_OPT_PRESENT,
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{GUILD_ID}/{ISLA_CHANNEL_ID}",
            )
        )

    @discord.ui.button(label=content.WELCOME_OPT_VESTIDOR, style=discord.ButtonStyle.primary)
    async def vestidor(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        cog = self.cog.bot.get_cog("Vestidor")
        if cog is None:
            await interaction.response.send_message(content.VESTIDOR_ERR_GENERIC, ephemeral=True)
            return
        await cog.open_panel(interaction)

    @discord.ui.button(label=content.WELCOME_OPT_GUIDE, style=discord.ButtonStyle.secondary)
    async def guide(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = discord.Embed(
            title=content.WELCOME_GUIDE_TITLE,
            color=content.WELCOME_EMBED_COLOR,
        )
        for name, description in content.WELCOME_GUIDE:
            embed.add_field(name=name, value=description, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self, cog: "Welcome"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label=content.WELCOME_VERIFY,
        style=discord.ButtonStyle.primary,
        custom_id="welcome:verify",
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        pool = db.pool()
        if pool is not None:
            try:
                await pool.execute(
                    "INSERT INTO verifications (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                    interaction.user.id,
                )
            except Exception:
                pass
        await interaction.followup.send(
            content=content.WELCOME_VERIFIED,
            view=OptionsView(self.cog),
            ephemeral=True,
        )


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(VerifyView(self))

    async def send_verification(
        self,
        member: discord.Member,
        channel: discord.TextChannel,
        public_message: discord.Message | None,
        embed: discord.Embed,
    ) -> None:
        # 1) DM: solo el nuevo miembro ve el boton
        try:
            dm = await member.create_dm()
            await dm.send(embed=embed, view=VerifyView(self))
            return
        except Exception:
            pass
        # 2) Hilo privado en #isla, solo el nuevo miembro (y el dueño) lo ve
        try:
            thread = await channel.create_thread(
                name=content.WELCOME_THREAD_NAME,
                type=discord.ChannelType.private_thread,
                invitable=False,
                reason="Verificación de nuevo miembro",
            )
            await thread.add_user(member)
            await thread.send(embed=embed, view=VerifyView(self))
            return
        except Exception:
            pass
        # 3) Ultimo recurso: boton en el mensaje publico
        if public_message is not None:
            try:
                await public_message.edit(view=VerifyView(self))
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID or member.bot:
            return
        channel = member.guild.get_channel(ISLA_CHANNEL_ID)
        if channel is None:
            return
        avatar = None
        try:
            avatar = await member.display_avatar.read()
        except Exception:
            avatar = None
        public_message = None
        try:
            png = banner.generate_welcome_banner(member.display_name, avatar)
            file = discord.File(io.BytesIO(png), filename="banner.png")
            embed = discord.Embed(
                description=content.WELCOME_TEXT,
                color=content.WELCOME_EMBED_COLOR,
            )
            embed.set_image(url="attachment://banner.png")
            public_message = await channel.send(
                content=content.WELCOME_MENTION.format(usuario=member.mention),
                embed=embed,
                file=file,
            )
        except Exception:
            embed = discord.Embed(
                description=content.WELCOME_TEXT,
                color=content.WELCOME_EMBED_COLOR,
            )
            public_message = await channel.send(
                content=content.WELCOME_MENTION.format(usuario=member.mention),
                embed=embed,
            )

        verify_embed = discord.Embed(
            description=content.WELCOME_TEXT,
            color=content.WELCOME_EMBED_COLOR,
        )
        await self.send_verification(member, channel, public_message, verify_embed)
