import asyncio
import discord
from discord.ext import commands, tasks
import config
import db


def sync_member_rank(member: discord.Member, db_path: str | None = None) -> dict | None:
    """Maps a Discord member's roles to the highest matching UPD rank in the database."""
    role_ids = {str(r.id) for r in member.roles}
    is_owner = str(member.id) == str(config.OWNER_DISCORD_ID)
    is_admin_role = (
        is_owner
        or bool(config.ADMIN_ROLE_ID and str(config.ADMIN_ROLE_ID) in role_ids)
        or member.guild_permissions.administrator
    )

    with db.connect(db_path) as conn:
        officer = conn.execute("SELECT * FROM officers WHERE discord_id = ?", (str(member.id),)).fetchone()
        if not officer and is_admin_role:
            top_rank = conn.execute("SELECT id FROM ranks ORDER BY level DESC LIMIT 1").fetchone()
            top_rank_id = top_rank["id"] if top_rank else None
            conn.execute(
                """INSERT INTO officers (discord_id, rp_name, badge, division, rank_id, status, is_admin)
                   VALUES (?, ?, ?, 'Office of the Chief', ?, 'active', 1)""",
                (str(member.id), member.display_name, "1001" if is_owner else str(member.id)[-4:], top_rank_id),
            )
            officer = conn.execute("SELECT * FROM officers WHERE discord_id = ?", (str(member.id),)).fetchone()
        if not officer:
            return None

        ranks = conn.execute(
            "SELECT id, level, discord_role_id FROM ranks WHERE discord_role_id IS NOT NULL ORDER BY level DESC"
        ).fetchall()
        matched_rank_id = officer["rank_id"]
        for rk in ranks:
            if rk["discord_role_id"] and str(rk["discord_role_id"]) in role_ids:
                matched_rank_id = rk["id"]
                break

        new_admin = 1 if (is_admin_role or officer["is_admin"]) else 0
        if matched_rank_id != officer["rank_id"] or new_admin != officer["is_admin"]:
            conn.execute(
                "UPDATE officers SET rank_id = ?, is_admin = ? WHERE id = ?",
                (matched_rank_id, new_admin, officer["id"]),
            )
        row = conn.execute(
            """SELECT o.*, r.name AS rank_name, COALESCE(r.level, 0) AS rank_level
               FROM officers o LEFT JOIN ranks r ON r.id = o.rank_id
               WHERE o.id = ?""",
            (officer["id"],),
        ).fetchone()
        return db.row_to_dict(row)


class RoleSyncCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.periodic_sync.start()

    def cog_unload(self):
        self.periodic_sync.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles:
            await asyncio.to_thread(sync_member_rank, after)

    @tasks.loop(minutes=30)
    async def periodic_sync(self):
        if not config.GUILD_ID:
            return
        guild = self.bot.get_guild(config.GUILD_ID)
        if not guild:
            return
        for member in guild.members:
            if not member.bot:
                await asyncio.to_thread(sync_member_rank, member)

    @periodic_sync.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(RoleSyncCog(bot))
