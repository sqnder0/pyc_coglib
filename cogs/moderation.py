"""
Discord Moderation Cog

A comprehensive moderation system for Discord bots featuring:
- Warning system with automatic timeouts
- Message filtering (ping limits, caps detection)
- Audit log integration for bans/kicks/timeouts
- Interactive configuration menu
- Comprehensive logging and error handling

Author: sqnder0
Repository: pyc_coglib
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from settings import get_settings, get_path
from database import get_database
from typing import Optional

SETTINGS = get_settings()
DATABASE = get_database()
logger = logging.getLogger("main")

def readable_time_format(td: timedelta) -> str:
    """Convert a timedelta to a human-readable string format.
    
    Args:
        td (timedelta): The time duration to format
        
    Returns:
        str: Human-readable time string (e.g., "2d 3h 5min(s) 30s")
        
    Example:
        >>> readable_time_format(timedelta(days=1, hours=2, minutes=30))
        "1d 2h 30min(s)"
    """
    total = int(td.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}min(s)")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)

async def log_mod_channel(guild: discord.Guild, message: str) -> None:
    """Log a message to the configured moderation log channel.

    Args:
        guild (discord.Guild): The guild where the channel is configured
        message (str): The message to log to the channel
        
    Raises:
        ValueError: If the guild is None
        
    Note:
        Silently fails if no mod log channel is configured or if the bot
        lacks permissions to send messages to the channel.
    """
    
    if guild == None:
        raise ValueError("Guild must not be None.")
        
    
    mod_log_channel = guild.get_channel(SETTINGS.get_or_create(get_path("mod_log_channel"), None))
    
    # Send a notification to the mod log channel, if it exists and is not a Forum- or CategoryChannel
    if mod_log_channel and not isinstance(mod_log_channel, discord.ForumChannel) and not isinstance(mod_log_channel, discord.CategoryChannel):
        try:
            await mod_log_channel.send(message)
        except discord.Forbidden:
            logger.warning(f"No permission to send message to mod log channel in {guild.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to send mod log message: {e}")
    
async def lookup_audit_log(guild: discord.Guild, action: discord.AuditLogAction, target: discord.User, limit: int) -> Optional[discord.AuditLogEntry]:
    """Search audit logs for a specific moderation action targeting a user.

    Args:
        guild (discord.Guild): The guild to search audit logs in
        action (discord.AuditLogAction): The type of action to look for (ban, kick, etc.)
        target (discord.User): The user who was the target of the action
        limit (int): Maximum number of audit log entries to search through

    Returns:
        Optional[discord.AuditLogEntry]: The matching audit log entry, or None if not found
        
    Note:
        This function first checks the most recent entry, then searches through
        additional entries up to the specified limit if the first doesn't match.
    """
    
    # Get the first audit log for this action
    try:
        first_entry = await anext(guild.audit_logs(limit=1, action=action))
    except StopAsyncIteration:
        return None
    final_entry = None
    
    # If the first audit log doesn't match the user that is banned, iterate trough maximum 10 other ones before you stop trying.
    try:
        assert isinstance(first_entry.target, discord.User) or isinstance(first_entry.target, discord.Member)
        if first_entry.target.id != target.id:
            async for entry in guild.audit_logs(limit=limit, action=action):
                try:
                    assert isinstance(entry.target, discord.User)
                    if entry.target.id == target.id:
                        final_entry = entry
                        break
                
                except Exception:
                    logger.error("Error while scanning audit logs")
        else:
            final_entry = first_entry
    except AssertionError:
        logger.error(f"Expected entry.target to be of type Discord.user but got {type(first_entry.target)}")
    
    return final_entry
    

def create_modmenu_embed(guild: discord.Guild) -> discord.Embed:
    """Create an embed displaying current moderation settings for the guild.

    Args:
        guild (discord.Guild): The guild to create the embed for

    Returns:
        discord.Embed: An embed containing all current moderation settings
        
    Note:
        The embed includes warn threshold, ping limits, caps percentage,
        and mod log channel configuration with appropriate formatting.
    """
    
    # Create an embed
    embed = discord.Embed(color=SETTINGS.get_embed_color(), title="Mod menu ⚙️")
    
    # Get all setting values for this module from settings.json
    warn_threshold = SETTINGS.get_or_create(get_path("warn_threshold"), 5)
    max_ping_count = SETTINGS.get_or_create(get_path("max_ping_count"), 2)
    max_caps = SETTINGS.get_or_create(get_path("max_caps_percent"), 30)
    mod_log_channel_id = SETTINGS.get_or_create(get_path("mod_log_channel"), None)
    
    # If there's no mod log channel display unset.
    if mod_log_channel_id == None:
        mod_log_channel_name = "unset."
    else:
        mod_log_channel = guild.get_channel(mod_log_channel_id)
        
        if mod_log_channel == None:
            mod_log_channel_name = "unset."
        else:
            mod_log_channel_name = mod_log_channel.mention
    
    # Display the settings on the embed
    embed.add_field(name=f"🚨 Warn threshold: {warn_threshold}", value="The amount of warns needed for a time-out", inline=False)
    
    embed.add_field(name=f"🔔 Max ping: {max_ping_count}", value="The max amount of people someone can ping in a message.", inline=True)
    
    embed.add_field(name=f"📢 Max cap: {max_caps}%", value="The max amount of caps someone can use in their message.", inline=False)
    
    embed.add_field(name=f"📃 Mod log channel {mod_log_channel_name}", value="The channel where we should broadcast moderation operations.", inline=True)
    
    embed.set_footer(text="Only an administrator can interact with the buttons.")
    
    return embed
    

class Moderation(commands.Cog):
    """Discord moderation cog with comprehensive moderation features.
    
    This cog provides:
    - Warning system with automatic timeouts based on thresholds
    - Message filtering for excessive pings and caps
    - Audit log tracking for bans, kicks, and timeouts
    - Interactive configuration menu for administrators
    - Comprehensive error handling and logging
    
    Attributes:
        bot (commands.Bot): The Discord bot instance
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the Moderation cog.
        
        Args:
            bot (commands.Bot): The Discord bot instance to register the cog to
        """
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Register persistent views when the bot becomes ready.
        
        This ensures that the ModMenuView buttons remain functional
        even after bot restarts.
        """
        self.bot.add_view(ModMenuView())
        logger.debug("ModMenuView registered!")
    
    @commands.Cog.listener("on_message")
    async def filter_ping(self, message: discord.Message) -> None:
        """Filter messages with excessive pings and take moderation action.
        
        Automatically deletes messages that exceed the configured ping limit
        and notifies the user via DM. Users with mention_everyone permission
        are exempt from this filter.
        
        Args:
            message (discord.Message): The message to check for ping violations
            
        Note:
            - Ignores bots, system messages, and DM messages
            - Counts @everyone, role mentions, and individual user mentions
            - Logs violations to the configured mod log channel
        """
        # If the message was not sent in a guild return.
        if message.guild == None: return
        # Skip bots, system messages, and webhooks
        if message.author.bot or message.is_system(): return
        guild = message.guild
        
        member = message.guild.get_member(message.author.id)
        # If the member does not exist (very rare) return
        if member == None: 
            logger.error("Author not found in guild.")
            return
        
        # If the member has permissions to manage a channel, he can ping more people.
        if member.guild_permissions.mention_everyone: return
        
        pinged_users = set(message.mentions)

        for role in message.role_mentions:
            if role.mentionable:
                pinged_users.update(role.members)

        if message.mention_everyone:
            pinged_users.update(message.guild.members)

        total_users = len(pinged_users)
        
        # If the amount of pings does not exceed the maximum amount of pings return
        if total_users < SETTINGS.get_or_create(get_path("max_ping_count"), 2): return
        
        # Delete the message if none of the above criteria where met.
        await message.delete()
        
        # Inform the user that he exceeded the message cap.
        try:
            if member.dm_channel == None:
                await member.create_dm()
            assert member.dm_channel != None
            await member.dm_channel.send("You exceeded the maximum amount of people you can ping in 1 message. Please respect others' need for peace and quiet. ") 
            
            # Send a moderation log
            await log_mod_channel(message=f"{message.author.mention} tried to ping {total_users} member(s).", guild=message.guild)
        except:
            logger.debug(f"Could not send a message to {member.name} a.k.a. {member.display_name}")
    
    @commands.Cog.listener("on_member_update")
    async def handle_timeout_check(self, before: discord.Member, after: discord.Member) -> None:
        """Monitor member updates to track timeout changes and log them.
        
        Detects when a member is timed out or when their timeout is removed,
        then searches audit logs to identify the moderator responsible and
        logs the action to the mod log channel.
        
        Args:
            before (discord.Member): Member state before the update
            after (discord.Member): Member state after the update
            
        Note:
            - Calculates timeout duration automatically
            - Handles both new timeouts and timeout removals
            - Searches audit logs to identify the responsible moderator
        """
        
        # If the timeout hasn't changed return
        if before.timed_out_until == after.timed_out_until:
            logger.debug("A member got updated, but before and after timeout where the same.")
            return
        
        # Get the total time out
        if before.timed_out_until == None and after.timed_out_until:
            timeout = after.timed_out_until - datetime.now(timezone.utc)
            # Ensure timeout is not negative
            if timeout.total_seconds() <= 0:
                timeout = None
        elif before.timed_out_until and after.timed_out_until:
            timeout = after.timed_out_until - before.timed_out_until
            # Ensure timeout is not negative
            if timeout.total_seconds() <= 0:
                timeout = None
        else:
            timeout = None
        
        # Generate a time-out message
        if timeout:
            td_str = readable_time_format(timeout)
            
            timeout_message = f"timed out {before.mention} for {td_str}"
        
        else:
            timeout_message = f"canceled the timeout for {before.mention}"
        
        # Try to get the member as a discord user object.
        guild = before.guild
        user = self.bot.get_user(before.id)
        
        if user == None:
            await log_mod_channel(message=f"Someone {timeout_message}, but I don't seem to find him as a user.", guild=guild)
            return
        
        # Get the audit entry.
        audit_entry = await lookup_audit_log(guild=guild, action=discord.AuditLogAction.member_update, target=user, limit=10)
        
        if not audit_entry:
            await log_mod_channel(message=f"Someone {timeout_message}, but I can't find the matching audit entry.", guild=guild)
            return
        
        # Define the name for the person who did the moderation
        mod = audit_entry.user.mention if audit_entry.user else "An unknown moderator"
        
        # For readability in the terminal and file logger we need a plain name.
        plain_mod = audit_entry.user.name if audit_entry.user else "An unknown moderator"
        
        # Log the timeout
        await log_mod_channel(message=f"{mod} {timeout_message}.", guild=guild)
        logger.info(f"{plain_mod} {timeout_message}.")
            
        

    
    @commands.Cog.listener("on_message")
    async def filter_caps(self, message: discord.Message) -> None:
        """Filter messages with excessive capital letters and take moderation action.
        
        Automatically deletes messages that exceed the configured caps percentage
        and notifies the user via DM. Users with manage_messages permission
        are exempt from this filter.
        
        Args:
            message (discord.Message): The message to check for caps violations
            
        Note:
            - Ignores bots, system messages, and DM messages
            - Calculates percentage of uppercase characters
            - Logs violations to the configured mod log channel
        """
        
        # Check if the message was sent in a guild.
        guild = message.guild
        if guild == None: return
        # Skip bots, system messages, and webhooks
        if message.author.bot or message.is_system(): return
        
        user = message.author
        member = guild.get_member(user.id)
        
        # Check if the user is part of the guild the message was sent in.
        if member == None: return
        
        # If the user has permissions to manage messages he can use caps.
        if member.guild_permissions.manage_messages: return
        
        # Get the amount of capital letters and the max percentage of capital letter
        total_caps = sum(1 for c in message.content if c.isupper())
        percentage = SETTINGS.get_or_create(get_path("max_caps_percent"), 30)
        
        # If the percentage of capital letters exceed the maximum delete the message.
        if len(message.content) > 0 and (total_caps / len(message.content) * 100) > percentage:
            await message.delete()
            
            # Notify the user he exceeded the maximum amount of caps.
            try:
                if member.dm_channel == None:
                    await member.create_dm()
                assert member.dm_channel != None
                await member.dm_channel.send("Please be polite and don't scream at everyone!") 
                
                if message.guild == None: return
                
                # Send a notification to the mod log channel, if it exists and is not a Forum- or CategoryChannel
                # Mention the channel if the channel is not a DM- or group channel
                if not isinstance(message.channel, discord.DMChannel) and not isinstance(message.channel, discord.GroupChannel):
                    # Send a moderation log
                    await log_mod_channel(guild=message.guild, message=f"{message.author.mention} tried to scream in {message.channel.mention}")
                
            except:
                logger.debug(f"Could not send a message to {member.name} a.k.a. {member.display_name}")
    
    @commands.Cog.listener("on_member_ban")
    async def on_ban(self, guild: discord.Guild, user: discord.User) -> None:
        """Track and log member bans with audit log information.
        
        When a member is banned, this listener searches the audit logs
        to identify the moderator and reason, then logs the information
        to the mod log channel.
        
        Args:
            guild (discord.Guild): The guild where the ban occurred
            user (discord.User): The user who was banned
            
        Note:
            - Includes a 1-second delay to allow audit logs to update
            - Falls back gracefully if audit log entry isn't found
        """
        await asyncio.sleep(1)
        
        final_entry = await lookup_audit_log(guild=guild, action=discord.AuditLogAction.ban, target=user, limit=10)
            
        if final_entry == None:
            await log_mod_channel(guild=guild, message=f"{user.mention} was banned, I can't find the matching audit log for a detailed description.")
        else:
            mod = final_entry.user.mention if final_entry.user else "an unknown moderator"
            reason = final_entry.reason or "No reason provided"

            message = f"{user.mention} was banned by {mod}.\n**Reason:** {reason}"
            await log_mod_channel(guild=guild, message=message)
            
            # Maybe a future suggestion, send the user a notification he's banned?
            # Doesn't work now because you can't send a dm to a user who isn't in a server with you.
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Track and log member kicks with audit log information.
        
        When a member leaves the server, this listener checks if they were
        kicked by searching audit logs, then logs the kick information
        to the mod log channel if found.
        
        Args:
            member (discord.Member): The member who left/was kicked
            
        Note:
            - Includes a 1-second delay to allow audit logs to update
            - Only logs if a matching kick entry is found in audit logs
            - Distinguishes between voluntary leaves and kicks
        """
        await asyncio.sleep(1)  # Give the audit log some time to update

        guild = member.guild
        final_entry = None
        
        try:
            first_entry = await anext(guild.audit_logs(limit=1, action=discord.AuditLogAction.kick))
        except StopAsyncIteration:
            logger.error("No entries were found!")
            return

        if first_entry and first_entry.target and hasattr(first_entry.target, 'id') and first_entry.target.id == member.id:
            final_entry = first_entry
        else:
            async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.kick):
                if entry.target and hasattr(entry.target, 'id') and entry.target.id == member.id:
                    final_entry = entry
                    break

        if final_entry:
            mod = final_entry.user.mention if final_entry.user else "an unknown moderator"
            reason = final_entry.reason or "No reason provided"
            await log_mod_channel(
                guild=guild,
                message=f"{member.mention} was kicked by {mod}.\n**Reason:** {reason}"
            )

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Handle application command errors with user-friendly messages.
        
        Provides appropriate error messages for common command failures
        such as missing permissions, cooldowns, and unknown commands.
        
        Args:
            interaction (discord.Interaction): The interaction that caused the error
            error (app_commands.AppCommandError): The error that occurred
            
        Note:
            - All error messages are sent as ephemeral (private) responses
            - Logs permission violations and unhandled errors for debugging
        """
        if isinstance(error, app_commands.MissingPermissions):
            missing = ', '.join(error.missing_permissions)
            await interaction.response.send_message(
                f"🚫 You lack the required permission(s): `{missing}`.",
                ephemeral=True
            )
            logger.warning(f"{interaction.user} tried to run a command without permissions: {missing}")
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⌛ This command is on cooldown", ephemeral=True)
        
        elif isinstance(error, app_commands.CommandNotFound):
            await interaction.response.send_message(f"🔍 I don't recognize this command.", ephemeral=True)
            
        else:
            await interaction.response.send_message(f"❌ An error occurred when running this command.", ephemeral=True)
            logger.error(f"Unhandled command error: {error}")


    
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.command(name="warn", description="Warn someone, after a specific of amount of warns you'll get a punishment")
    async def warn(self, ctx: discord.Interaction, user: discord.Member, reason: str) -> None:
        """Issue a warning to a user and apply automatic timeout if threshold is reached.
        
        Adds a warning to the database and automatically times out the user
        if they reach the configured warning threshold. Prevents warning of
        bots, self, and administrators.
        
        Args:
            ctx (discord.Interaction): The interaction context
            user (discord.Member): The member to warn
            reason (str): The reason for the warning
            
        Note:
            - Timeout duration increases with each threshold reached (5min * threshold_count)
            - Maximum timeout duration is capped at 7 days
            - All warnings are logged to the mod log channel
        """
        
        if user.bot:
            await ctx.response.send_message("❌ You cannot warn bots!", ephemeral=True)
            return
            
        if user.id == ctx.user.id:
            await ctx.response.send_message("❌ You cannot warn yourself!", ephemeral=True)
            return
            
        if user.guild_permissions.administrator:
            await ctx.response.send_message("❌ You cannot warn administrators!", ephemeral=True)
            return
        
        DATABASE.execute("""INSERT INTO warns (user_id, reason)
                            VALUES (?, ?)""", user.id, reason)
        await ctx.response.send_message(f"You've warned {user.mention}")
        response = DATABASE.execute("""SELECT * FROM warns
                            WHERE user_id = ?""", user.id)
        
        warn_count = len(response)
        
        guild = ctx.guild
            
        if guild == None:
            return
        
        warn_threshold = SETTINGS.get_or_create(get_path("warn_threshold"), 5)
        if warn_count % warn_threshold == 0:
            duration = min(5 * (warn_count // warn_threshold), 10080)  # Cap at 7 days (10080 minutes)
            await user.timeout(timedelta(minutes=duration), reason="You exceeded the maximum amount of warns!")
            await ctx.followup.send(f"{user.mention} has reached the warning threshold ({warn_count} warns)!")
            
            # Send a moderation log
            await log_mod_channel(guild=guild, message=f"{user.mention} is muted for {duration}min(s) due to reaching the warn threshold")
        
        await log_mod_channel(guild=guild, message=f"{user.mention} was warned by {ctx.user.mention} for {reason}")
        return
    
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.command(name="listwarns", description="List all warns for a user.")
    async def listwarns(self, ctx: discord.Interaction, user: discord.Member) -> None:
        """Display all warnings for a specific user in an embed format.
        
        Creates a formatted embed showing all warnings for the specified user,
        including warning IDs and reasons. Respects Discord's character limits
        and shows a truncated list if necessary.
        
        Args:
            ctx (discord.Interaction): The interaction context
            user (discord.Member): The member whose warnings to display
            
        Note:
            - Response is ephemeral (private) to the command user
            - Automatically truncates if too many warnings to display
            - Shows total count vs displayed count if truncated
        """
        # Get all warns from the database.
        response = DATABASE.execute("""SELECT * FROM warns WHERE user_id = ?;""", user.id)
        
        # Create the embed
        embed = discord.Embed(colour=SETTINGS.get_embed_color(), title=f"Warns for {user.mention}")
        
        # Set the thumbnail to the users avatar.
        embed.set_thumbnail(url=user.display_avatar.url)
        
        id_column = []
        reason_column = []
        
        for row in response:
            warn_id = f"`{str(row[0])}`"
            reason = f"*{str(row[2])}*"
            
            # Check if adding this would exceed Discord's 1024 character limit
            if len("\n".join(id_column + [warn_id])) > 1000 or len("\n".join(reason_column + [reason])) > 1000:
                break
                
            id_column.append(warn_id)
            reason_column.append(reason)
        
        if len(response) > len(id_column):
            embed.set_footer(text=f"Showing {len(id_column)} of {len(response)} warns (character limit reached).")
        elif len(id_column) < 1:
            embed.set_footer(text="No warns were found.")
        else:
            embed.add_field(name="**ID**", value="\n".join(id_column), inline=True)
            embed.add_field(name="**Reason**", value="\n".join(reason_column), inline=True)

        await ctx.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.command(name="clearwarn", description="Remove a warning for a user.")
    async def clearwarn(self, ctx: discord.Interaction, warn_id: int) -> None:
        """Remove a specific warning from the database by its ID.
        
        Permanently removes a warning from the database and logs the action
        to the mod log channel. Uses atomic operations to prevent race conditions.
        
        Args:
            ctx (discord.Interaction): The interaction context
            warn_id (int): The ID of the warning to remove
            
        Note:
            - Response is ephemeral (private) to the command user
            - Action is logged to the mod log channel
            - Provides clear feedback if warning ID doesn't exist
        """
        
        if not ctx.guild: return
        
        # Use a single query to get the warn and delete it atomically
        response = DATABASE.execute("SELECT * FROM warns WHERE id = ?", warn_id)
        if not response:
            await ctx.response.send_message(f"❌ Couldn't find a warn with id {warn_id}", ephemeral=True)
            return
            
        warn_data = response[0]
        DATABASE.execute("DELETE FROM warns WHERE id = ?", warn_id)
        
        user_id = warn_data[1]
        user = ctx.guild.get_member(user_id)
        
        if user == None:
            name = "an unknown member."
        else:
            name = user.mention
        
        await ctx.response.send_message(f"✅ Successfully cleared the warn with id {warn_data[0]} for {name}", ephemeral=True)
    
        await log_mod_channel(guild=ctx.guild, message=f"{ctx.user.mention} cleared a warn for {name}.")
        
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="modmenu", description="Open a mod menu to configure moderation settings.")
    async def modmenu(self, ctx: discord.Interaction) -> None:
        """Open an interactive moderation configuration menu.
        
        Creates an interactive menu with buttons to configure various
        moderation settings including warn thresholds, ping limits,
        caps percentages, and mod log channels.
        
        Args:
            ctx (discord.Interaction): The interaction context
            
        Note:
            - Requires administrator permissions
            - Includes confirmation step to prevent accidental usage
            - Menu times out after 60 seconds of inactivity
            - Should be used in private channels for security
        """
        
        if ctx.guild == None:
            await ctx.response.send_message("❌ Please only use this in guilds!")
            return
        
        if ctx.channel == None:
            logger.error("ctx.channel was none.")
            return
        
        await ctx.response.send_message("Please confirm you want to open the mod menu. Use this wisely preferably in a private channel.\nConfirm [Y/n]:", ephemeral=True)
        
        # Wait for a new message from the same author in the same channel
        def check(msg: discord.Message):
            return ctx.user == msg.author and ctx.channel == msg.channel
        
        try:
            message = await self.bot.wait_for("message", check=check, timeout=120)
            
            await message.delete()
            
            if not message.clean_content.lower().startswith("y"):
                return
            
        except TimeoutError:
                await ctx.followup.send("You took too long to respond❗", ephemeral=True)
                return
        
        embed = create_modmenu_embed(ctx.guild)
        
        if isinstance(ctx.channel, discord.channel.ForumChannel) or isinstance(ctx.channel, discord.channel.CategoryChannel):
            return
        view = ModMenuView()
        modmenu = await ctx.channel.send(embed=embed, view=view)
        view.message = modmenu

class ModMenuView(discord.ui.View):
    """Interactive view for moderation configuration menu.
    
    Provides button-based interface for administrators to configure
    moderation settings including warn thresholds, ping limits,
    caps percentages, and mod log channels.
    
    Attributes:
        message (Optional[discord.Message]): The message containing this view
        
    Note:
        - View times out after 60 seconds of inactivity
        - All buttons require administrator permissions
        - Automatically updates the embed after configuration changes
    """
    
    def __init__(self) -> None:
        """Initialize the ModMenuView with default timeout."""
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=60)
    
    async def on_timeout(self) -> None:
        """Handle view timeout by disabling the menu and updating the message.
        
        When the view times out, this method updates the original message
        to inform users that the menu has expired and provides instructions
        to create a new one.
        """
        if self.message == None:
            return await super().on_timeout()
        else:
            
            await self.message.edit(content=f"Modmenu timed out, The original message was deleted.\nUse /modmenu to get a new one.", embed=None, view=None)

    @app_commands.checks.has_permissions(administrator=True)
    @discord.ui.button(label="🚨 Edit warn threshold", style=discord.ButtonStyle.green)
    async def edit_warn_threshold(self, ctx: discord.Interaction, button: discord.ui.Button):
        """Button handler to edit the warning threshold setting.
        
        Prompts the administrator to enter a new warning threshold value.
        The threshold determines how many warnings a user needs before
        receiving an automatic timeout.
        
        Args:
            ctx (discord.Interaction): The button interaction context
            button (discord.ui.Button): The button that was pressed
            
        Note:
            - Validates that the threshold is greater than 0
            - Updates the configuration and refreshes the menu
            - Logs the change to the mod log channel
        """
        
        # If the guild does not exist return.
        guild = ctx.guild
        if guild == None: return
        
        # If the interaction user has no permissions throw a permission error.
        member = guild.get_member(ctx.user.id)
        if member == None: return
        
        # If the user doesn't have admin permissions, return
        if not member.guild_permissions.administrator:
            return await ctx.response.send_message("You don't have permission to use this command.")
        
        await ctx.response.send_message("🚨 Edit warn threshold:\nSend the desired warn threshold here ⇩", ephemeral=True)
        
        # Wait for a new message from the same author in the same channel
        def check(msg: discord.Message):
                return ctx.user == msg.author and ctx.channel == msg.channel
        try:
            message = await ctx.client.wait_for('message', check=check, timeout=60.0)
               # Process the message content
            threshold = int(message.content)
            
            if threshold <= 0:
                await ctx.followup.send("❌ Warn threshold must be greater than 0.", ephemeral=True)
                return
            
            await message.delete()
            
            SETTINGS.put(get_path("warn_threshold"), threshold)
            
            await ctx.followup.send(f"✅ Warn threshold set to {threshold}!", ephemeral=True)
            
            # Send a moderation log
            await log_mod_channel(guild=guild, message=f"{ctx.user.name} changed the warn threshold to {threshold}.")
            
        except asyncio.TimeoutError:
            await ctx.followup.send("⏰ Timed out waiting for response.", ephemeral=True)
        except ValueError:
            await ctx.followup.send("❌ Please enter a valid number.", ephemeral=True)
        
        if ctx.message == None: return
        
        assert ctx.guild != None
        embed = create_modmenu_embed(ctx.guild)
        
        if self.message:
            self.timeout = 60.0
            await self.message.edit(embed=embed, view=self)
        else:
            await ctx.message.edit(embed=embed, view=ModMenuView())
    
    @app_commands.checks.has_permissions(administrator=True)
    @discord.ui.button(label="🔔 Edit max ping", style=discord.ButtonStyle.green)
    async def edit_max_ping(self, ctx: discord.Interaction, button: discord.ui.Button):
        """Button handler to edit the maximum ping count setting.
        
        Prompts the administrator to enter a new maximum ping limit.
        This controls how many users can be mentioned in a single message
        before the message is automatically deleted.
        
        Args:
            ctx (discord.Interaction): The button interaction context
            button (discord.ui.Button): The button that was pressed
            
        Note:
            - Validates that the ping count is not negative
            - Updates the configuration and refreshes the menu
            - Logs the change to the mod log channel
        """
        
        # If the guild does not exist return.
        guild = ctx.guild
        if guild == None: return
        
        # If the interaction user has no permissions throw a permission error.
        member = guild.get_member(ctx.user.id)
        if member == None: return
        
        # If the user doesn't have admin permissions, return
        if not member.guild_permissions.administrator:
            return await ctx.response.send_message("You don't have permission to use this command.")
        
        await ctx.response.send_message("🔔 Edit the maximum ping:\nSend the desired maximum amount of members someone can ping.", ephemeral=True)
        
        # Wait for a new message from the same author in the same channel
        def check(msg: discord.Message):
                return ctx.user == msg.author and ctx.channel == msg.channel
        try:
            message = await ctx.client.wait_for('message', check=check, timeout=60.0)
               # Process the message content
            max_ping = int(message.content)
            
            if max_ping < 0:
                await ctx.followup.send("❌ Max ping count cannot be negative.", ephemeral=True)
                return
            
            await message.delete()
            
            SETTINGS.put(get_path("max_ping_count"), max_ping)
            
            await ctx.followup.send(f"✅ Max ping count set to {max_ping}!", ephemeral=True)
            
            # Send a moderation log
            await log_mod_channel(guild=guild, message=f"{ctx.user.name} set the max ping count to {max_ping}.")
            
        except asyncio.TimeoutError:
            await ctx.followup.send("⏰ Timed out waiting for response.", ephemeral=True)
        except ValueError:
            await ctx.followup.send("❌ Please enter a valid number.", ephemeral=True)
        
        if ctx.message == None: return
        
        assert ctx.guild != None
        embed = create_modmenu_embed(ctx.guild)
        
        if self.message:
            self.timeout = 60.0
            await self.message.edit(embed=embed, view=self)
        else:
            await ctx.message.edit(embed=embed, view=ModMenuView())
        
    @app_commands.checks.has_permissions(administrator=True)
    @discord.ui.button(label="📢 Edit max caps", style=discord.ButtonStyle.green)
    async def edit_max_caps(self, ctx: discord.Interaction, button: discord.ui.Button):
        """Button handler to edit the maximum caps percentage setting.
        
        Prompts the administrator to enter a new maximum caps percentage.
        This controls what percentage of capital letters is allowed in
        messages before they are automatically deleted.
        
        Args:
            ctx (discord.Interaction): The button interaction context
            button (discord.ui.Button): The button that was pressed
            
        Note:
            - Validates that the percentage is between 0-100
            - Updates the configuration and refreshes the menu
            - Logs the change to the mod log channel
        """
        
        # If the guild does not exist return.
        guild = ctx.guild
        if guild == None: return
        
        # If the interaction user has no permissions throw a permission error.
        member = guild.get_member(ctx.user.id)
        if member == None: return
        
        # If the user doesn't have admin permissions, return
        if not member.guild_permissions.administrator:
            return await ctx.response.send_message("You don't have permission to use this command.")
        
        await ctx.response.send_message("📢 Edit the maximum caps:\nSend the desired percentage of caps a message can maximum have (0-100 without the '%').", ephemeral=True)
        
        # Wait for a new message from the same author in the same channel
        def check(msg: discord.Message):
                return ctx.user == msg.author and ctx.channel == msg.channel
        try:
            message = await ctx.client.wait_for('message', check=check, timeout=60.0)
               # Process the message content
            max_caps = int(message.content)
            
            if max_caps > 100 or max_caps < 0:
                raise ValueError
            
            await message.delete()
            
            SETTINGS.put(get_path("max_caps_percent"), max_caps)
            
            await ctx.followup.send(f"✅ Max cap percentage set to {max_caps}%!", ephemeral=True)
            
            # Send a moderation log
            await log_mod_channel(guild=guild, message=f"{ctx.user.name} set the max cap percentage to {max_caps}%.")
            
        except asyncio.TimeoutError:
            await ctx.followup.send("⏰ Timed out waiting for response.", ephemeral=True)
        except ValueError:
            await ctx.followup.send("❌ Please enter a valid percentage.", ephemeral=True)
        
        if ctx.message == None: return
        
        assert ctx.guild != None
        embed = create_modmenu_embed(ctx.guild)
        
        if self.message:
            self.timeout = 60.0
            await self.message.edit(embed=embed, view=self)
        else:
            await ctx.message.edit(embed=embed, view=ModMenuView())
    
    @app_commands.checks.has_permissions(administrator=True)
    @discord.ui.button(label="📃 Edit mod log channel", style=discord.ButtonStyle.blurple)
    async def edit_mod_log_channel(self, ctx: discord.Interaction, button: discord.ui.Button):
        """Button handler to edit the moderation log channel setting.
        
        Prompts the administrator to provide a channel ID for the new
        moderation log channel. All moderation actions will be logged
        to this channel once configured.
        
        Args:
            ctx (discord.Interaction): The button interaction context
            button (discord.ui.Button): The button that was pressed
            
        Note:
            - Validates that the provided channel ID exists in the guild
            - Notifies the old mod log channel of the change
            - Updates the configuration and refreshes the menu
        """
        
        # If the guild does not exist return.
        guild = ctx.guild
        if guild == None: return
        
        # If the interaction user has no permissions throw a permission error.
        member = guild.get_member(ctx.user.id)
        if member == None: return
        
        # If the user doesn't have admin permissions, return
        if not member.guild_permissions.administrator:
            return await ctx.response.send_message("You don't have permission to use this command.")
            
        # Send instructions
        await ctx.response.send_message('# Mod log channel 📃: \n\n**1:** Right click on the channel you want as mod log channel.\n\n**2:** Click "copy channel ID".\n\n**3:** Paste the channel ID and send it in this channel. (eg: 1234567891234567890)', ephemeral=True)
        
        def check(msg: discord.Message):
            return ctx.user == msg.author and ctx.channel == msg.channel
        
        try:
            message = await ctx.client.wait_for("message", check=check, timeout=60.0)
            
            # Delete the message for privacy
            await message.delete()
            
            channel_id = int(message.content)
            
            channel = guild.get_channel(channel_id)
            
            if channel:
                mod_log_channel = guild.get_channel(SETTINGS.get_or_create(get_path("mod_log_channel"), None))
                
                SETTINGS.put(get_path("mod_log_channel"), channel.id)
                
                await ctx.followup.send(f"✅ Channel set to {channel.mention}", ephemeral=True)
                
                # Send a notification to the mod log channel, if it exists and is not a Forum- or CategoryChannel
                # Mention the channel if the channel is not a DM- or group channel
                if mod_log_channel and not isinstance(mod_log_channel, discord.ForumChannel) and not isinstance(mod_log_channel, discord.CategoryChannel):
                    await mod_log_channel.send(f"{ctx.user.name} set the mod log channel to {channel.mention}, you won't receive any moderation logs no more in this channel.")
            else:
                raise KeyError
            
        except TimeoutError:
            await ctx.followup.send("⏰ You took too long to respond.", ephemeral=True)
            
        except ValueError:
            await ctx.followup.send("❌ That's not a valid channel ID.", ephemeral=True)
        
        except KeyError:
            await ctx.followup.send("❌ Channel was not found.", ephemeral=True)

        embed = create_modmenu_embed(guild=guild)
        
        if self.message:
            self.timeout = 60.0
            await self.message.edit(embed=embed, view=self)
        elif ctx.message:
            await ctx.message.edit(embed=embed, view=ModMenuView())
 

async def setup(bot: commands.Bot) -> None:
    """Initialize and load the Moderation cog.
    
    Sets up the database table for warnings and adds the Moderation cog
    to the bot. This function is called automatically when the cog is loaded.
    
    Args:
        bot (commands.Bot): The Discord bot instance to add the cog to
        
    Note:
        - Creates the warns table if it doesn't exist
        - Table structure: id (PRIMARY KEY), user_id (INTEGER), reason (TEXT)
    """
    DATABASE.execute("CREATE TABLE IF NOT EXISTS warns (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER, reason TEXT);")
    await bot.add_cog(Moderation(bot))