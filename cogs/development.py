"""
PyC CogLib Development Cog

Development and debugging utilities for Discord bot management.
Provides commands for hot-reloading cogs and other development operations
that help during bot development and maintenance.

Features:
- Hot reload all registered cogs without restarting the bot
- Proper module reloading with import refresh
- Error handling and logging for reload operations
- Requires moderate_members permission for safety

Commands:
- /reload: Unload, refresh, and reload all bot cogs

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

import importlib
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger("main")

class DevelopmentCog(commands.Cog):
    """
    Development utilities for bot management.
    
    This cog provides commands useful during development and debugging,
    including the ability to reload cogs without restarting the entire bot.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the Development cog.
        
        Args:
            bot (commands.Bot): The Discord bot instance
        """
        self.bot = bot
    
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.command(name="reload", description="Reload the bot's registered cogs.")
    async def reloadcogs(self, ctx: discord.Interaction):
        """
        Hot reload all currently loaded bot cogs.
        
        Args:
            ctx (discord.Interaction): The interaction context
            
        This command performs a complete reload cycle:
        1. Unloads all currently loaded extensions
        2. Refreshes the Python modules from disk
        3. Reloads the extensions with the updated code
        
        This allows for code changes to take effect without restarting
        the entire bot process. Requires moderate_members permission.
        """
        
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
    
    #TODO: Add a /sync command, to not sync commands every time you load the bot
        

async def setup(bot: commands.Bot):
    """
    Set up the Development cog.
    
    Args:
        bot (commands.Bot): The bot instance to add the cog to
    """
    await bot.add_cog(DevelopmentCog(bot))