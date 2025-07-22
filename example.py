import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import logging
from datetime import datetime
from settings import get_settings
import json

# Load environment variables from .env file
load_dotenv()

# Get the token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup log directory
if not os.path.exists("logs/"):
    os.mkdir("logs")
    
#Setup logging.
logger = logging.getLogger("main")

formatter = logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s", "%H:%M")
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(filename=f"logs/{datetime.now().strftime("%d-%m-%Y")}.log", mode="w")

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Change to logging.INFO on production.
logger.setLevel(logging.DEBUG)

# Get the settings
settings = get_settings()

# Set up bot intents and bot instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Sync slash commands on ready
@bot.event
async def on_ready():
    await tree.sync()
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
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("Something went wrong, contact an administrator if necessary", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    if TOKEN != None:
        logger.info("Bot token found, starting bot.")
        bot.run(TOKEN)
    else:
        logger.error("Token was not found!")