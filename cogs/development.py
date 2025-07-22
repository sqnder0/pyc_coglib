import importlib
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger("main")

class DevelopmentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.command(name="reload", description="Reload the bot's registered cogs.")
    async def reloadcogs(self, ctx: discord.Interaction):
        
        reloaded = []
        
        for ext in list(self.bot.extensions):
            await self.bot.unload_extension(ext)
            
            logger.debug(f"Unloaded extension called: {ext}")
            
            module = importlib.reload(importlib.import_module(ext))
            logger.debug(f"Reloaded the python file.")
            
            await self.bot.load_extension(ext)
            logger.debug(f"Loaded extension")
            
            reloaded.append(ext)

        
        message = f"Re-loaded {len(reloaded)} extension(s)"
        
        logger.debug(message)
        await ctx.response.send_message(message)
        

async def setup(bot: commands.Bot):
    await bot.add_cog(DevelopmentCog(bot))