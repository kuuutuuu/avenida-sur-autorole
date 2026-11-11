import json
import os

import discord
from discord import app_commands
from discord.ext import commands

import content
import db

GUILD_ID = int(os.environ["GUILD_ID"])
GUILD_OBJ = discord.Object(id=GUILD_ID)
OWNER_ID = int(os.environ.get("OWNER_ID", "310866269299671052"))
POLL_COLOR = 0x90A4AE


def parse_options(raw: str) -> list[str]:
    seen = set()
    options = []
    for line in raw.splitlines():
        value = line.strip()
        if not value or value.lower() in seen:
            continue
        seen.add(value.lower())
        options.append(value[:80])
        if len(options) == 10:
            break
    return options


def results_text(
    question: str,
    options: list[str],
    counts: dict[int, int],
    closed: bool,
) -> str:
    total = sum(counts.values())
    lines = [f"**{question}**", ""]
    for index, option in enumerate(options):
        votes = counts.get(index, 0)
        percent = round(votes * 100 / total) if total else 0
        lines.append(f"**{option}** — {votes} ({percent}%)")
    if closed:
        lines.append("")
        lines.append(f"**{content.POLL_CLOSED}**")
    return "\n".join(lines)


class PollModal(discord.ui.Modal):
    def __init__(self, cog: "Encuesta"):
        super().__init__(title=content.POLL_MODAL_TITLE, timeout=600)
        self.cog = cog
        self.question = discord.ui.TextInput(
            label=content.POLL_QUESTION_LABEL,
            placeholder=content.POLL_QUESTION_PLACEHOLDER,
            max_length=200,
            required=True,
        )
        self.options = discord.ui.TextInput(
            label=content.POLL_OPTIONS_LABEL,
            placeholder=content.POLL_OPTIONS_PLACEHOLDER,
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.add_item(self.question)
        self.add_item(self.options)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.create_poll(
            interaction,
            str(self.question.value).strip(),
            parse_options(str(self.options.value)),
        )


class Encuesta(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="encuesta", description=content.POLL_CMD_DESC)
    @app_commands.guilds(GUILD_OBJ)
    async def encuesta(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PollModal(self))

    def build_view(self, poll_id: int, options: list[str]) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        for index, option in enumerate(options):
            view.add_item(
                discord.ui.Button(
                    label=option,
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"poll:{poll_id}:{index}",
                )
            )
        view.add_item(
            discord.ui.Button(
                label=content.POLL_CLOSE,
                style=discord.ButtonStyle.danger,
                custom_id=f"poll:close:{poll_id}",
            )
        )
        return view

    async def create_poll(
        self,
        interaction: discord.Interaction,
        question: str,
        options: list[str],
    ) -> None:
        if len(options) < 2:
            await interaction.response.send_message(
                content.POLL_ERROR_OPTIONS, ephemeral=True
            )
            return
        pool = db.pool()
        if pool is None:
            await interaction.response.send_message(
                content.VESTIDOR_ERR_GENERIC, ephemeral=True
            )
            return
        try:
            row = await pool.fetchrow(
                "INSERT INTO polls (channel_id, question, options, created_by) "
                "VALUES ($1,$2,$3::jsonb,$4) RETURNING id",
                interaction.channel_id,
                question,
                json.dumps(options),
                interaction.user.id,
            )
            poll_id = row["id"]
            embed = discord.Embed(
                title=content.POLL_EMBED_TITLE,
                description=results_text(question, options, {}, False),
                color=POLL_COLOR,
            )
            await interaction.response.send_message(
                embed=embed, view=self.build_view(poll_id, options)
            )
            message = await interaction.original_response()
            await pool.execute(
                "UPDATE polls SET message_id=$1 WHERE id=$2",
                message.id,
                poll_id,
            )
        except Exception:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    content.VESTIDOR_ERR_GENERIC, ephemeral=True
                )

    async def update_poll(self, poll_id: int) -> None:
        pool = db.pool()
        if pool is None:
            return
        poll = await pool.fetchrow("SELECT * FROM polls WHERE id=$1", poll_id)
        if poll is None or poll["message_id"] is None:
            return
        raw_options = poll["options"]
        options = json.loads(raw_options) if isinstance(raw_options, str) else raw_options
        rows = await pool.fetch(
            "SELECT option_index, COUNT(*) AS total FROM poll_votes "
            "WHERE poll_id=$1 GROUP BY option_index",
            poll_id,
        )
        counts = {row["option_index"]: row["total"] for row in rows}
        channel = self.bot.get_channel(poll["channel_id"])
        if channel is None:
            return
        try:
            message = await channel.fetch_message(poll["message_id"])
        except discord.HTTPException:
            return
        embed = discord.Embed(
            title=content.POLL_EMBED_TITLE,
            description=results_text(
                poll["question"], options, counts, poll["closed"]
            ),
            color=POLL_COLOR,
        )
        view = None if poll["closed"] else self.build_view(poll_id, options)
        try:
            await message.edit(embed=embed, view=view)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = (interaction.data or {}).get("custom_id", "")
        if not custom_id.startswith("poll:"):
            return
        parts = custom_id.split(":")
        await interaction.response.defer(ephemeral=True)
        pool = db.pool()
        if pool is None:
            await interaction.followup.send(
                content.VESTIDOR_ERR_GENERIC, ephemeral=True
            )
            return
        try:
            if parts[1] == "close":
                poll_id = int(parts[2])
                poll = await pool.fetchrow(
                    "SELECT created_by, closed FROM polls WHERE id=$1", poll_id
                )
                if poll is None or poll["closed"]:
                    await interaction.followup.send(
                        content.POLL_CLOSED, ephemeral=True
                    )
                    return
                if (
                    interaction.user.id != poll["created_by"]
                    and interaction.user.id != OWNER_ID
                ):
                    await interaction.followup.send(
                        content.POLL_ONLY_CREATOR, ephemeral=True
                    )
                    return
                await pool.execute(
                    "UPDATE polls SET closed=TRUE WHERE id=$1", poll_id
                )
                await self.update_poll(poll_id)
                await interaction.followup.send(
                    content.POLL_CLOSED, ephemeral=True
                )
            else:
                poll_id = int(parts[1])
                option_index = int(parts[2])
                poll = await pool.fetchrow(
                    "SELECT closed FROM polls WHERE id=$1", poll_id
                )
                if poll is None or poll["closed"]:
                    await interaction.followup.send(
                        content.POLL_CLOSED, ephemeral=True
                    )
                    return
                await pool.execute(
                    "INSERT INTO poll_votes (poll_id, user_id, option_index) "
                    "VALUES ($1,$2,$3) ON CONFLICT (poll_id, user_id) "
                    "DO UPDATE SET option_index=EXCLUDED.option_index",
                    poll_id,
                    interaction.user.id,
                    option_index,
                )
                await interaction.followup.send(
                    content.POLL_VOTE_OK, ephemeral=True
                )
                await self.update_poll(poll_id)
        except Exception:
            try:
                await interaction.followup.send(
                    content.VESTIDOR_ERR_GENERIC, ephemeral=True
                )
            except Exception:
                pass
