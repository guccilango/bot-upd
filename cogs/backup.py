import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
import discord
from discord import app_commands
from discord.ext import commands, tasks
import config
import db


def create_sqlite_backup_bytes(db_path: str | None = None) -> bytes:
    tmp_path = Path(tempfile.mktemp(suffix=".db"))
    try:
        with db.connect(db_path) as src:
            dst = sqlite3.connect(str(tmp_path))
            with dst:
                src.backup(dst)
            dst.close()
        return tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


class BackupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_backup.start()

    def cog_unload(self):
        self.daily_backup.cancel()

    @tasks.loop(hours=24)
    async def daily_backup(self):
        if not config.BACKUP_CHANNEL_ID:
            return
        ch = self.bot.get_channel(config.BACKUP_CHANNEL_ID)
        if not ch:
            try:
                ch = await self.bot.fetch_channel(config.BACKUP_CHANNEL_ID)
            except Exception:
                return
        await self._send_backup_to_channel(ch, reason="Automated 24h Snapshot")

    @daily_backup.before_loop
    async def before_backup(self):
        await self.bot.wait_until_ready()

    async def _send_backup_to_channel(self, channel, reason: str):
        import io
        raw = await asyncio.to_thread(create_sqlite_backup_bytes)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        fname = f"upd_records_{stamp}.db"
        await channel.send(
            content=f"🗄️ **UPD SQLite Database Backup** (`{fname}`) — *{reason}*",
            file=discord.File(io.BytesIO(raw), filename=fname),
        )

    @app_commands.command(name="backup", description="[Admin] Trigger an immediate SQLite database backup")
    async def manual_backup(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.Member) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        import io
        raw = await asyncio.to_thread(create_sqlite_backup_bytes)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        fname = f"upd_records_{stamp}.db"
        await interaction.followup.send(
            content="✅ Database snapshot generated:",
            file=discord.File(io.BytesIO(raw), filename=fname),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BackupCog(bot))
