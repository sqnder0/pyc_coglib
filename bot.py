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
settings = get_settings()

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
        #TODO: Add a /sync command, to not sync commands every time you load the bot
        sync_before = datetime.now()
        synced = await bot.tree.sync()
        delta = datetime.now() - sync_before
        logger.info(f"Synced {len(synced)} command(s) in {delta.seconds // 60}m {delta.seconds % 60}s")
    except Exception:
        logger.exception("An exception happened during command synchronization:")

# Example slash command
@bot.tree.command(name="ping", description="Check the bots latency (response time).")
async def ping(ctx: discord.Interaction):
    await ctx.response.send_message(f"Pong! {round(bot.latency, 2)}ms")
    
async def load_extensions(bot):
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
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