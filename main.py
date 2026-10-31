import asyncio
import logging
import discord
from discord.ext import commands
import uvicorn
import api
import config
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("upd.main")


class UPDBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for ext in ("cogs.sync", "cogs.aprovacao", "cogs.emitir", "cogs.admin", "cogs.backup"):
            await self.load_extension(ext)
        if config.GUILD_ID:
            guild_obj = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            log.info("Synced slash commands to Guild ID %s", config.GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Synced global slash commands")


async def main():
    db.init_db()
    uv_cfg = uvicorn.Config(api.app, host="0.0.0.0", port=config.PORT, log_level="info")
    server = uvicorn.Server(uv_cfg)

    token = (config.DISCORD_TOKEN or "").strip()
    if token and not token.startswith("your_"):
        bot = UPDBot()
        api.set_bot_instance(bot)
        async with bot:
            await asyncio.gather(bot.start(token), server.serve())
    else:
        log.warning("DISCORD_TOKEN not set; running FastAPI server only on port %s", config.PORT)
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
