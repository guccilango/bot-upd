import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import config
import core
import db
from cogs.sync import sync_member_rank


def _is_command_admin(interaction: discord.Interaction, officer: dict | None) -> bool:
    if officer and officer.get("is_admin"):
        return True
    if isinstance(interaction.user, discord.Member):
        if interaction.user.guild_permissions.administrator:
            return True
        if config.ADMIN_ROLE_ID and any(str(r.id) == str(config.ADMIN_ROLE_ID) for r in interaction.user.roles):
            return True
    return False


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admitir", description="[Admin] Admit or update an officer in the UPD Records System")
    @app_commands.describe(
        membro="Discord member to admit",
        nome_rp="Officer's full Roleplay Name (used for cursive signature)",
        badge="Badge / Serial number (e.g., 4109)",
        divisao="Departmental division (e.g., Patrol Division, Detective Bureau)",
        admin="Grant system administrator privileges",
    )
    async def admitir(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        nome_rp: str,
        badge: str,
        divisao: str = "Patrol Division",
        admin: bool = False,
    ):
        caller = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not _is_command_admin(interaction, caller):
            await interaction.response.send_message("❌ Only UPD System Administrators can admit officers.", ephemeral=True)
            return

        with db.connect() as conn:
            default_rank = conn.execute("SELECT id FROM ranks ORDER BY level ASC LIMIT 1").fetchone()
            rank_id = default_rank["id"] if default_rank else None
            existing = conn.execute("SELECT id FROM officers WHERE discord_id = ?", (str(membro.id),)).fetchone()
            if existing:
                conn.execute(
                    """UPDATE officers
                       SET rp_name = ?, badge = ?, division = ?, status = 'active', is_admin = ?
                       WHERE discord_id = ?""",
                    (nome_rp.strip(), badge.strip(), divisao.strip(), 1 if admin else 0, str(membro.id)),
                )
            else:
                conn.execute(
                    """INSERT INTO officers (discord_id, rp_name, badge, division, status, rank_id, is_admin, admitted_by)
                       VALUES (?, ?, ?, ?, 'active', ?, ?, ?)""",
                    (
                        str(membro.id),
                        nome_rp.strip(),
                        badge.strip(),
                        divisao.strip(),
                        rank_id,
                        1 if admin else 0,
                        caller["id"] if caller else None,
                    ),
                )

        synced = await asyncio.to_thread(sync_member_rank, membro)
        rk_name = (synced or {}).get("rank_name") or "Cadet"
        await interaction.response.send_message(
            f"✅ **{rk_name} {nome_rp}** (Badge `#{badge}`) admitted and active for {membro.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="suspender", description="[Admin] Suspend an officer from issuing or approving documents")
    async def suspender(self, interaction: discord.Interaction, membro: discord.Member):
        caller = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not _is_command_admin(interaction, caller):
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        with db.connect() as conn:
            conn.execute("UPDATE officers SET status = 'suspended' WHERE discord_id = ?", (str(membro.id),))
        await interaction.response.send_message(f"⛔ {membro.mention} has been suspended.", ephemeral=True)

    @app_commands.command(name="mapearcargo", description="[Admin] Link a Discord Role to a UPD Rank for automatic sync")
    @app_commands.describe(nivel="Rank level (1=Cadet, 5=Corporal, 11=Commander, 14=Chief)", cargo="Discord role")
    async def mapear_cargo(self, interaction: discord.Interaction, nivel: int, cargo: discord.Role):
        caller = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not _is_command_admin(interaction, caller):
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        with db.connect() as conn:
            row = conn.execute("SELECT id, name FROM ranks WHERE level = ?", (nivel,)).fetchone()
            if not row:
                await interaction.response.send_message(f"❌ Rank level `{nivel}` not found.", ephemeral=True)
                return
            conn.execute("UPDATE ranks SET discord_role_id = NULL WHERE discord_role_id = ?", (str(cargo.id),))
            conn.execute("UPDATE ranks SET discord_role_id = ? WHERE id = ?", (str(cargo.id), row["id"]))
        await interaction.response.send_message(
            f"✅ Mapped Discord role {cargo.mention} → **{row['name']} (Level {nivel})**.",
            ephemeral=True,
        )

    @app_commands.command(name="revogar", description="[Admin] Revoke an approved document so public verification shows REVOKED")
    async def revogar(self, interaction: discord.Interaction, numero: str, motivo: str):
        caller = await asyncio.to_thread(core.get_officer_by_discord, str(interaction.user.id))
        if not _is_command_admin(interaction, caller):
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        if caller and not caller.get("is_admin"):
            caller["is_admin"] = 1
        try:
            doc = await asyncio.to_thread(
                core.revoke_document, numero, caller or {"id": 0, "is_admin": 1}, motivo
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to revoke: {e}", ephemeral=True)
            return
        await interaction.response.send_message(
            f"🚫 Document **{doc['control_no'] or doc['id']}** has been marked as **REVOKED**.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
