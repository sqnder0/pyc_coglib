# Cog for customizing the bot's appearance
import discord
from discord.ext import commands
from discord import app_commands
from enum import Enum
import logging
import asyncio
from datetime import datetime, timedelta
from settings import get_settings, get_path
from database import get_database
from typing import Optional

SETTINGS = get_settings()
DATABASE = get_database()
logger = logging.getLogger("main")

def create_modmenu_embed(guild):
    embed = discord.Embed(color=SETTINGS.get_embed_color(), title="Mod menu ⚙️")
    
    warn_threshold = SETTINGS.get_or_create(get_path("warn_threshold"), 5)
    max_ping_count = SETTINGS.get_or_create(get_path("max_ping_count"), 2)
    max_caps = SETTINGS.get_or_create(get_path("max_caps_percent"), 30)
    mod_log_channel_id = SETTINGS.get_or_create(get_path("mod_log_channel"), None)
    
    if mod_log_channel_id == None:
        mod_log_channel_name = "unset."
    else:
        mod_log_channel = guild.get_channel(mod_log_channel_id)
        
        if mod_log_channel == None:
            mod_log_channel_name = "unset."
        else:
            mod_log_channel_name = mod_log_channel.mention
    
    embed.add_field(name=f"🚨 Warn threshold: {warn_threshold}", value="The amount of warns needed for a time-out", inline=False)
    
    embed.add_field(name=f"🔔 Max ping: {max_ping_count}", value="The max amount of people someone can ping in a message.", inline=True)
    
    embed.add_field(name=f"📢 Max cap: {max_caps}%", value="The max amount of caps someone can use in their message.", inline=False)
    
    embed.add_field(name=f"📃 Mod log channel {mod_log_channel_name}", value="The channel where we should broadcast moderation operations.", inline=True)
    
    embed.set_footer(text="Only you can interact with the buttons.")
    
    return embed
    

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ModMenuView())
        logger.debug("ModMenuView registered!")
    
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.command(name="warn", description="Warn someone, after a specific of amount of warns you'll get a punishment")
    async def warn(self, ctx: discord.Interaction, user: discord.Member, reason: str):
        DATABASE.execute("""INSERT INTO warns (user_id, reason)
                            VALUES (?, ?)""", user.id, reason)
        await ctx.response.send_message(f"You've warned {user.mention}")
        response = DATABASE.execute("""SELECT * FROM warns
                            WHERE user_id = ?""", user.id)
        
        warn_count = len(response)
        if warn_count % SETTINGS.get_or_create(get_path("warn_threshold"), 5):
            duration = timedelta(minutes=5)
            await user.timeout(duration, reason="You exceeded the maximum amount of warns!")
            await ctx.followup.send(f"{user.mention} has reached the warning threshold ({warn_count} warns)!")
        
        return
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="modmenu", description="Open a mod menu to configure moderation settings")
    async def modmenu(self, ctx: discord.Interaction):
        
        if ctx.guild == None:
            await ctx.response.send_message("❌ Please only use this in guilds!")
            return
        
        if ctx.channel == None:
            logger.error("ctx.channel was none.")
            return
        
        #FIXME: This boolean expression does not what it has to do!
        if str(ctx.channel.type) == "private":
            await ctx.response.send_message("❌ Only use this command in private channels for safety measurements.", ephemeral=True)
            return
            
        
        embed = create_modmenu_embed(ctx.guild)
        

        await ctx.response.send_message(embed=embed, view=ModMenuView())

# TODO: Limit mass ping per message
# TODO: Caps filter
# TODO: Mod logs channel
# TODO: Button system
# TODO: Mass ban
class ModMenuView(discord.ui.View):
    def __init__(self):
        # Make sure the buttons never expire
        super().__init__(timeout=None)

    @app_commands.checks.has_permissions(moderate_members=True)
    @discord.ui.button(label="🚨 Edit warn threshold", style=discord.ButtonStyle.green)
    async def create_ticket_button(self, ctx: discord.Interaction, button: discord.ui.Button):
        await ctx.response.send_message("🚨 Edit warn threshold:\nSend the desired warn threshold here ⇩", ephemeral=True)
        
        # Wait for a new message from the same author in the same channel
        def check(msg):
                return ctx.user == msg.author and ctx.channel == msg.channel
        try:
            message = await ctx.client.wait_for('message', check=check, timeout=60.0)
               # Process the message content
            threshold = int(message.content)
            
            await message.delete()
            
            SETTINGS.put(get_path("warn_threshold"), threshold)
            
            await ctx.followup.send(f"✅ Warn threshold set to {threshold}!", ephemeral=True)
            
        except asyncio.TimeoutError:
            await ctx.followup.send("⏰ Timed out waiting for response.", ephemeral=True)
        except ValueError:
            await ctx.followup.send("❌ Please enter a valid number.", ephemeral=True)
        
        if ctx.message == None: return
        
        assert ctx.guild != None
        embed = create_modmenu_embed(ctx.guild)
        
        await ctx.message.edit(embed=embed, view=ModMenuView())
        
        

async def setup(bot: commands.Bot):
    DATABASE.execute("CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, reason TEXT);")
    await bot.add_cog(Moderation(bot))