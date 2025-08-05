"""
PyC CogLib Discord Bot Main Module

A modular Discord bot framework built with discord.py, featuring:
- Hot-swappable cog system for modular functionality
- Optional web panel integration for remote management
- Persistent settings and database storage
- Comprehensive logging system
- Graceful shutdown handling

This is the main entry point for the bot. It handles initialization,
extension loading, and provides both standalone and web panel modes.

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import logging
from datetime import datetime
from settings import get_settings
import signal
import asyncio
from database import get_database

# Load environment variables from .env file
load_dotenv()

# Get the token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup log directory
if not os.path.exists("logs/"):
    os.mkdir("logs")
    
#Setup logging.
logger = logging.getLogger("main")

LOG_FILENAME = f"""logs/{datetime.now().strftime("%d-%m-%Y")}.log"""

formatter = logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s", "%H:%M")
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(filename=LOG_FILENAME, mode="a")

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Change to logging.INFO on production.
logger.setLevel(logging.DEBUG)

# Get the settings
SETTINGS = get_settings()

# Set the project dir
project_dir = os.path.dirname(os.path.abspath(__file__))

# Setup the database
DATABASE = get_database()

# Setup api default values, this won't be used if you don't have any webpanels installed
HOST = "localhost"
PORT = 5566

# Set up bot intents and bot instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Sync slash commands on ready
@bot.event
async def on_ready():
    """
    Event handler triggered when the bot successfully connects to Discord.
    
    This function:
    1. Logs the successful connection
    2. Loads all available cogs from the cogs/ directory
    3. Syncs slash commands with Discord
    4. Reports timing information for both operations
    """
    logger.info(f"Logged in as {bot.user}")
    
    logger.info("Loading cogs...")
    cogs_before = datetime.now()
    try:
        await load_extensions(bot=bot)
        delta = datetime.now() - cogs_before
        logger.info(f"Cogs loaded in {delta.seconds // 60}m {delta.seconds % 60}s")
    except:
        logger.exception("An exception happened during the cog loading.")  
    
    try:
        sync_before = datetime.now()
        synced = await bot.tree.sync()
        delta = datetime.now() - sync_before
        logger.info(f"Synced {len(synced)} command(s) in {delta.seconds // 60}m {delta.seconds % 60}s")
    except Exception:
        logger.exception("An exception happened during command synchronization:")
    
    
    logger.info("Verifying guild restrictions")
    
    # Leave all guilds that where joined when offline
    original_guild_id = SETTINGS.get_or_create("guild", None)

    if original_guild_id is None and bot.guilds:
        # First run: save the first guild
        main_guild = bot.guilds[0]
        SETTINGS.put("guild", main_guild.id)
        logger.info(f"Registered initial guild: {main_guild.name} (ID: {main_guild.id})")
        # Leave any extras (safety)
        for guild in bot.guilds[1:]:
            logger.info(f"Leaving unauthorized guild: {guild.name} (ID: {guild.id})")
            await guild.leave()

    else:
        # Enforce restriction if multiple guilds exist
        for guild in bot.guilds:
            if guild.id != original_guild_id:
                logger.info(f"Leaving unauthorized guild: {guild.name} (ID: {guild.id})")
                await guild.leave()
    

# Make sure the bot can't join another guild
@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Event handler triggered when the bot joins a new guild.
    
    This function makes sure that the bot can't be in more then 1 guild.
    The first guild is saved in settings.json. 
    """
    
    allowed_guild_id = SETTINGS.get_or_create("guild", None)

    if allowed_guild_id is None:
        SETTINGS.put("guild", guild.id)
        logger.info(f"Registered new allowed guild: {guild.name} (ID: {guild.id})")
    elif guild.id != allowed_guild_id:
        logger.info(
            f"Bot invited to unauthorized guild: {guild.name} (ID: {guild.id}), "
            f"but restricted to guild ID {allowed_guild_id}. Leaving."
        )
        await guild.leave()

# Example slash command
@bot.tree.command(name="ping", description="Check the bots latency (response time).")
async def ping(ctx: discord.Interaction):
    """
    A simple ping command that responds with the bot's latency.
    
    Args:
        ctx (discord.Interaction): The interaction context from Discord
        
    Returns:
        A message showing the bot's current latency in milliseconds
    """
    await ctx.response.send_message(f"Pong! {round(bot.latency, 2)}ms")
    
async def load_extensions(bot):
    """
    Load all Python files from the cogs/ directory as bot extensions.
    
    Args:
        bot (commands.Bot): The bot instance to load extensions into
        
    This function automatically discovers and loads all .py files in the
    cogs/ directory, making it easy to add new functionality without
    modifying the main bot file.
    """
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """
    Global error handler for application commands (slash commands).
    
    Args:
        interaction (discord.Interaction): The interaction that caused the error
        error (app_commands.AppCommandError): The error that occurred
        
    This handler provides user-friendly error messages and logs detailed
    error information for debugging purposes.
    """
    original_error = getattr(error, "original", error)
    cmd_name = interaction.command.name if interaction.command else "<unknown>"

    if isinstance(original_error, app_commands.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("🚫 You don't have permission to use this command", ephemeral=True)
        else:
            await interaction.followup.send("🚫 You don't have permission to use this command", ephemeral=True)
        
        logger.warning(
            f"{interaction.user} tried to use `{cmd_name}` without required permissions: {original_error.missing_permissions}"
        )
    else:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Something went wrong. Contact an admin.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Something went wrong. Contact an admin.", ephemeral=True)
        
        logger.error(
            f"{interaction.user} failed to use command `{cmd_name}` due to: {original_error}",
            exc_info=True
        )
        
# Run the bot
async def bot_setup():
    """
    Set up and run the Discord bot with graceful shutdown handling.
    
    This function:
    1. Sets up signal handlers for SIGINT and SIGTERM
    2. Starts the bot with the provided token
    3. Waits for shutdown signals
    4. Gracefully closes database connections and bot connections
    
    The function handles missing tokens gracefully and ensures proper cleanup.
    """
    stop_event = asyncio.Event()
    
    def handle_shutdown(*_):
        stop_event.set()

    # Listen for termination
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
        # Start bot
    if TOKEN is not None:
        logger.info("Bot token found, starting bot.")
        bot_task = asyncio.create_task(bot.start(TOKEN))

        # Wait for shutdown
        await stop_event.wait()

        logger.debug("Shutdown detected, saving database...")
        DATABASE.close()

        logger.info("Closing bot...")
        await bot.close()
        await bot_task
    else:
        logger.error("Bot token not found.")


async def main():
    """
    Main entry point for the application.
    
    This function determines whether to run in standalone mode or with
    the optional web panel integration. If webpanels/ directory exists,
    it starts both the bot and web API concurrently.
    """
    if os.path.exists(os.path.join(project_dir, "webpanels/")):
        from api import get_server, set_bot, set_host, set_port
        
        # Configure the api
        set_host(HOST)
        set_port(PORT)
        set_bot(bot)
        
        server = get_server()

        # Run both the bot and the API as an asyncio task
        bot_task = asyncio.create_task(bot_setup())
        api_task = asyncio.create_task(server.serve())

        await asyncio.gather(bot_task, api_task)
        
    else:
        # Just run the bot in the main thread
        await bot_setup()

if __name__ == "__main__":
    asyncio.run(main())