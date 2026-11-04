import asyncio
import discord
from discord.ext import commands, tasks
import config
from core import match_rank_for_role_ids, parse_nickname_badge_and_name
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
        matched_rk = match_rank_for_role_ids(conn, role_ids)
        officer = conn.execute("SELECT * FROM officers WHERE discord_id = ?", (str(member.id),)).fetchone()
        if not officer and (is_admin_role or matched_rk):
            top_rank = conn.execute("SELECT id FROM ranks ORDER BY level DESC LIMIT 1").fetchone()
            rank_id = matched_rk["id"] if matched_rk else (top_rank["id"] if top_rank else None)
            badge, rp_name = parse_nickname_badge_and_name(member.display_name, str(member.id))
            division = (
                "Office of the Chief"
                if is_admin_role
                else "Criminal Investigation Division"
                if (matched_rk and matched_rk["name"].upper() == "CID")
                else "Patrol Division"
            )
            conn.execute(
                """INSERT INTO officers (discord_id, rp_name, badge, division, rank_id, status, is_admin)
                   VALUES (?, ?, ?, ?, ?, 'active', ?)""",
                (
                    str(member.id),
                    rp_name,
                    "1001" if is_owner else badge,
                    division,
                    rank_id,
                    1 if is_admin_role else 0,
                ),
            )
            officer = conn.execute("SELECT * FROM officers WHERE discord_id = ?", (str(member.id),)).fetchone()
        if not officer:
            return None

        matched_rank_id = matched_rk["id"] if matched_rk else officer["rank_id"]
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
