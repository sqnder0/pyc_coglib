# Cog for customizing the bot's appearance
import discord
from discord.ext import commands
from discord import app_commands
from enum import Enum
import logging
from settings import get_settings, get_path
from typing import Optional

SETTINGS = get_settings()

class StatusEnum(Enum):
    online = "online"
    idle = "idle"
    dnd = "dnd"
    invisible = "invisible"

class ActivityEnum(Enum):
    playing = "playing"
    listening = "listening"
    watching = "watching"
    streaming = "streaming"
    competing = "competing"
    none = "none"

async def load_status(bot: commands.Bot, ctx: Optional[discord.Interaction] = None):
    """Load the bots status from settings.

    Args:
        bot (commands.Bot): The bot whose settings you are trying to load.
        ctx (Optional[discord.Interaction], optional): The discord interaction if applicable
    """
    
    logger = logging.getLogger("main")
    
    activity = ActivityEnum(SETTINGS.get_or_create(get_path("presence.activity"), "none"))
    status = StatusEnum(SETTINGS.get_or_create(get_path("presence.status"), "online"))
    message = SETTINGS.get_or_create(get_path("presence.message"), "")
    
    status_map = {
        StatusEnum.online: discord.Status.online,
        StatusEnum.idle: discord.Status.idle,
        StatusEnum.dnd: discord.Status.dnd,
        StatusEnum.invisible: discord.Status.invisible,
    }
        
    activity_map = {
        ActivityEnum.playing: discord.Game(message),
        ActivityEnum.listening: discord.Activity(type=discord.ActivityType.listening, name=message),
        ActivityEnum.watching: discord.Activity(type=discord.ActivityType.watching),
        ActivityEnum.streaming: discord.Activity(type=discord.ActivityType.streaming, name=message),
        ActivityEnum.competing: discord.Activity(type=discord.ActivityType.competing, name=message)
    }
        
    if activity != ActivityEnum.none:
        await bot.change_presence(
            status=status_map[status],
            activity=activity_map[activity]
        )
            
        logger.info(f"Presence set to {status.name}: {activity.name} {message}.")
        
        if ctx != None:
            await ctx.response.send_message(f"Presence set to {status.name}: {activity.name} {message}.", ephemeral=True)
                  
    else:
        await bot.change_presence(
            status=status_map[status]
        )
        
        if ctx != None:
            await ctx.response.send_message("Presence changed", ephemeral=True)
    
    logger.info(f"presence loaded.")
    
    return

class Customization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("main")
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="set_presence", description="Set the presence of the bot.")
    async def set_presence(self, ctx: discord.Interaction,
        status: StatusEnum,
        activity: ActivityEnum,
        message: str
    ):
        
        SETTINGS.put(get_path("presence.activity"), activity.name)
        SETTINGS.put(get_path("presence.status"), status.name)
        SETTINGS.put(get_path("presence.message"), message)
        
        await load_status(self.bot, ctx)
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="set_embed_color", description="Set the bot's embeds color")
    async def set_embed_color(self, ctx: discord.Interaction, color: str):
        raw = color.strip().lstrip("#").lower()
        
        if len(raw) != 6 or any(c not in "0123456789abcdef" for c in raw):
            message = f"{color} is not a valid base-16 hex string. Make sure the hex starts with a # and contains 6 characters ranging from 0-f (e.g: #5865F2)"
            self.logger.warning(message)
            
        
        else:
            SETTINGS.put("embed.color", color)
            message = f"embed color set to {color}"
            self.logger.info(message)
            
        await ctx.response.send_message(message, ephemeral=True) 
    
async def setup(bot: commands.Bot):
    await load_status(bot)
    await bot.add_cog(Customization(bot))