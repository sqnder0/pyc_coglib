"""
PyC CogLib Ticket System Cog

A comprehensive Discord ticket system with interactive buttons and configuration.
Provides users with a way to create private support channels and staff with
tools to manage and claim tickets.

Features:
- Interactive ticket creation with persistent buttons
- Configurable ticket categories and descriptions
- Ticket claiming system for staff
- Automatic channel creation with proper permissions
- Ticket closure with user notifications
- Persistent button views that survive bot restarts

Commands:
- /ticket: Create the ticket creation embed with buttons
- /ticketconfig: Configure ticket system settings

Interactive Elements:
- Create Ticket button: Creates a new support ticket
- Claim Ticket button: Staff can claim tickets
- Close Ticket button: Close and delete ticket channels

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from settings import get_settings, get_path
import json
import logging
import random

SETTINGS = get_settings()
logger = logging.getLogger("main")

class TicketCog(commands.Cog):
    """
    Discord ticket system management.
    
    This cog provides a complete ticket system with configurable settings,
    interactive buttons, and staff management tools.
    """
    
    def __init__(self, bot):
        """
        Initialize the Ticket cog.
        
        Args:
            bot (commands.Bot): The Discord bot instance
        """
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """
        Re-register persistent views when the bot starts.
        
        This ensures that ticket buttons continue to work even after
        the bot restarts, maintaining functionality for existing ticket embeds.
        """
        ticket_buttons = TicketButtons()
        self.bot.add_view(ticket_buttons)
        logger.info("Ticket buttons have been re-registered.")
        
    @commands.Cog.listener()
    async def on_resumed(self):
        """
        Re-register persistent views when the bot resumes connection.
        
        Similar to on_ready, this ensures button functionality is maintained
        when the bot reconnects to Discord.
        """
        ticket_buttons = TicketButtons()
        await self.bot.add_view(ticket_buttons)
        
    @app_commands.command(name="ticket")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket(self, interaction: discord.Interaction):
        """
        Create a ticket creation embed with interactive buttons.
        
        Args:
            interaction (discord.Interaction): The interaction context
            
        This command creates an embed with a "Create ticket" button that users
        can click to open new support tickets. The embed uses configured
        descriptions and styling.
        """
        
        await interaction.response.send_message("Configuring the embed...", ephemeral=True)
        
        description = SETTINGS.get_or_create(get_path("embed.description"), "Please set a ticket description first!")
        
        try:
            embed = discord.Embed(title="Create ticket ✉️", description=description, color=SETTINGS.get_embed_color())
        except Exception as e:
            logger.error(f"❌ Error creating embed: {e}")
    
        
        # Try to set the tumbnail
        thumbnail = SETTINGS.get_or_create("embed.thumbnail", "")
        embed.set_thumbnail(url=thumbnail)
    
        
        try:
            view = TicketButtons()
        except Exception as e:
            logger.error(f"❌ There was an exception configuring the buttons {e}")
        
        
        try:
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"❌ There was an exception sending the embeds {e}")
        
        await interaction.followup.send("Finished", ephemeral=True)

    @app_commands.command(name="ticketconfig")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(choice=[
        app_commands.Choice(name="set category", value="setCategory"),
        app_commands.Choice(name="set ticket description", value="ticketDesc"),
        app_commands.Choice(name="set channel description", value="channelDesc"),
    ])
    async def ticketconfig(self, ctx: discord.Interaction, choice: app_commands.Choice[str]):
        """
        Configure ticket system settings.
        
        Args:
            ctx (discord.Interaction): The interaction context
            choice (app_commands.Choice[str]): The configuration option to set
            
        Available configuration options:
        - setCategory: Set the Discord category where tickets are created
        - ticketDesc: Set the description for ticket creation embeds
        - channelDesc: Set the description shown in new ticket channels
        
        This command provides an interactive configuration flow where users
        are prompted to provide the necessary information via follow-up messages.
        """
        if choice.value == "setCategory":
            
            # Send instructions
            await ctx.response.send_message('# Ticket category 📃: \n\n**1:** Right click on the category you want as ticket category.\n\n**2:** Click "copy category ID".\n\n**3:** Paste the category ID and send it in this channel. (eg: 1234567891234567890)', ephemeral=True)
            
            # Wait for a new message from the same author in the same channel
            def check(msg):
                return ctx.user == msg.author and ctx.channel == msg.channel
            
            try:
                message = await self.bot.wait_for("message", check=check, timeout=120)
                # Delete the message after sent
                await message.delete()
                if message.content.isdigit() and ctx.guild != None:
                    category = discord.utils.get(ctx.guild.categories, id=int(message.content))
                    if category:
                        # Update the current ticket description
                        SETTINGS.put(get_path("ticket.category"), message.content)

                        # Confirm message
                        logger.info(f"Ticket category set to {category.name}")
                        await ctx.followup.send(f"Ticket category successfully set to {category.mention} 😀.", ephemeral=True)
                    else:
                        await ctx.followup.send("The id provided is not a valid category❗", ephemeral=True)
                else:
                    await ctx.followup.send("The id provided is not a valid number❗", ephemeral=True)
            
            # When someone takes longer then 2 mins to respond.
            except TimeoutError:
                await ctx.followup.send("You took too long to respond❗", ephemeral=True)

        elif choice.value == "ticketDesc":
            
            # Send instructions
            await ctx.response.send_message("# Ticket description\nSet the description of the ticket creation embed.\n\n**1:** Send the description in this channel.\n\n**2:** Run /ticket in the ticket channel.", ephemeral=True)
            
            # Wait for a new message from the same author in the same channel
            def check(msg):
                return ctx.user == msg.author and ctx.channel == msg.channel
            try:
                message = await self.bot.wait_for("message", check=check, timeout=120)
                # Delete the message after sent
                await message.delete()
                
                # Update the settings file
                SETTINGS.put(get_path("ticket.description"), message.content)
                
                logger.info(f"Ticket description updated (see settings).")
                await ctx.followup.send("Description set successfully 😀.", ephemeral=True)
                
            # When someone takes longer then 2 mins to respond.
            except TimeoutError:
                await ctx.followup.send("You took too long to respond❗", ephemeral=True)

        elif choice.value == "channelDesc":
            
            # Send instructions
            await ctx.response.send_message("# Ticket channel description\nSet the description of the embed sent when creating a ticket.\n\n**1:** Send the description in this channel.\n\n**2:** Run /ticket in the ticket channel.", ephemeral=True)
            
            # Wait for a new message from the same author in the same channel
            def check(msg):
                return ctx.user == msg.author and ctx.channel == msg.channel
            try:
                message = await self.bot.wait_for("message", check=check, timeout=120)
                # Delete the message after sent
                await message.delete()
                
                # Update the settings file
                SETTINGS.put(get_path("embed.description"), message.content)
                
                logger.info("Embed description updated (see settings)")
                await ctx.followup.send("Description set successfully 😀.", ephemeral=True)
            
            # When someone takes longer then 2 mins to respond.
            except TimeoutError:
                await ctx.followup.send("You took too long to respond❗", ephemeral=True)

class TicketButtons(discord.ui.View):
    """
    Persistent view containing the ticket creation button.
    
    This view contains the main "Create ticket" button that users click
    to open new support tickets. The view is persistent, meaning it
    survives bot restarts.
    """
    
    def __init__(self):
        """
        Initialize the ticket buttons view.
        
        Sets timeout to None to make the view persistent across bot restarts.
        """
        # Make sure the buttons never expire
        super().__init__(timeout=None)
    
    # Initialize the button
    @discord.ui.button(label="Create ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle ticket creation when the button is clicked.
        
        Args:
            interaction (discord.Interaction): The button interaction
            button (discord.ui.Button): The button that was clicked
            
        This method:
        1. Validates the user and guild
        2. Checks for configured ticket category
        3. Creates a new text channel with appropriate permissions
        4. Sends a ticket information embed with control buttons
        5. Notifies the user of successful ticket creation
        """
        logger.debug("Creating ticket...")
        
        # Get the user and guild
        user = interaction.user
        guild = interaction.guild
        
        if guild == None:
            logger.error("Guild not found!")
            await interaction.response.send_message("Guild not found!")
            return
        
        if user == None:
            logger.error("User not found!")
            await interaction.response.send_message("User not found!")
            return
        
        # Get the user as a member of the guild.
        member = guild.get_member(user.id)
        
        if member == None:
            logger.error(f"User not found as member in {guild}")
            return
        
        # Get the category where the ticket needs to be created
        category_id = int(SETTINGS.get_or_create(get_path("ticket.category"), "0"))
        
        if category_id == 0:
            logger.error("Ticket creation failed: category not initialized.")
            await interaction.response.send_message("Ticket category not set: run /ticketconfig setCategory")
        
        category = discord.utils.get(guild.categories, id=category_id)
        
        # Check if the category exists
        if not category:
            logger.error("Ticket category not found.")
            await interaction.response.send_message("No category found!", ephemeral=True)
            return
        
        ticket_id = random.randrange(1000, 9999)
        
        # Create the channel
        channel = await guild.create_text_channel(name=f"{user.display_name}︱{ticket_id}", category=category)
        
        await channel.edit(sync_permissions=True)
        
        overwrite = channel.overwrites_for(user)
        overwrite.update(send_messages=True, read_messages=True)
        
        await channel.set_permissions(member, overwrite=overwrite)
        
        # Let the user know about the ticket
        await interaction.response.send_message(f"Ticket created {channel.mention}", ephemeral=True)
        
        # Send the ticket description
        ticketChannelDescription = SETTINGS.get_or_create(get_path("ticket.description"), "No description set")
        
        embed = discord.Embed(title="🎫 Ticket", description=ticketChannelDescription, color=discord.Color.green())
        embed.add_field(name="Ticket id", value=ticket_id, inline=False)
        embed.add_field(name="Created by", value=user.name, inline=False)
        embed.add_field(name="Status", value="open", inline=False)
        embed.add_field(name="Instructions", value="Our team will be with you shortly. Please avoid tagging staff members repeatedly.", inline=False)

        await channel.send(embed=embed, view=TicketControlButtons())


class TicketControlButtons(discord.ui.View):
    """
    Persistent view containing ticket management buttons for staff.
    
    This view appears in ticket channels and provides staff with
    buttons to claim and close tickets.
    """
    
    def __init__(self):
        """
        Initialize the ticket control buttons view.
        
        Sets timeout to None to make the view persistent.
        """
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle ticket claiming when the button is clicked.
        
        Args:
            interaction (discord.Interaction): The button interaction
            button (discord.ui.Button): The button that was clicked
            
        This method:
        1. Validates the interaction and message
        2. Prevents users from claiming their own tickets
        3. Updates the ticket embed to show who claimed it
        4. Provides feedback to the claiming user
        """
        # Update the embed with the claim information
        
        # Get the embed and guild
        message = interaction.message
        guild = interaction.guild
        
        if message == None:
            logger.error("Ticket message not found.")
            await interaction.response.send_message("An error occurred, please contact an admin if necessary.")
            return

        if guild == None:
            logger.error("Guild not found.")
            await interaction.response.send_message("An error occurred, please contact an admin if necessary.")
            return
        
        embed = message.embeds[0]
        
        user_name = message.embeds[0].fields[1].value
        
        if user_name == None:
            logger.error("User who opened the ticket not found.")
            return interaction.response.send_message("User who opened the ticket not found.")
        
        opened_by = guild.get_member_named(user_name)
        
        if interaction.user == opened_by:
            logger.debug(f"{user_name} tried to claim his own ticket.")
            await interaction.response.send_message("You can't claim your own ticket.", ephemeral=True)
            return
        
        else:
            embed.set_field_at(2, name="Status", value=f"Claimed by {interaction.user.mention}", inline=False)
            await message.edit(embed=embed, view=self)
            await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}", ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle ticket closure when the button is clicked.
        
        Args:
            interaction (discord.Interaction): The button interaction
            button (discord.ui.Button): The button that was clicked
            
        This method:
        1. Validates permissions (only claimant can close claimed tickets)
        2. Sends a notification to the ticket creator
        3. Deletes the ticket channel
        4. Handles both claimed and unclaimed ticket states
        """
        # Check if the user has permission to close the ticket
        
        # Get the embed and guild
        message = interaction.message
        guild = interaction.guild
        
        if message == None:
            logger.error("Ticket message not found.")
            await interaction.response.send_message("An error occurred, please contact an admin if necessary.")
            return

        if guild == None:
            logger.error("Guild not found.")
            await interaction.response.send_message("An error occurred, please contact an admin if necessary.")
            return
        
        status = message.embeds[0].fields[2].value
        
        if status == None:
            logger.warning("Ticket status not found, changing to open...")
            status = "open"
            logger.info("Ticket status changed to open.")
        
        # If the ticket is claimed
        if status != "open":
            
            logger.debug("obtaining user id")
            
            # Get the user who claimed the ticket
            user_id = status.split(" ")[-1].strip("<@!>")
            user_id = int(user_id)
            user = guild.get_member(user_id)
            
            if user == None:
                logger.error("No one has claimed this ticket, but it's not open anymore")
                await interaction.response.send_message("Something is malicious with your ticket, please try and open a new one. If that doesn't work, contact an admin.")
                return
                
            logger.debug(f"User: {user}")
            logger.debug(f"Interaction user: {interaction.user}")
            
            if user != interaction.user:
                await interaction.response.send_message(f"You can't close this ticket, it's claimed by {user.display_name}", ephemeral=True)
                return
        
            else:
                # Get the owner of the ticket and send him a message
                user_name = message.embeds[0].fields[1].value
                
                if user_name != None:
                    member = guild.get_member_named(user_name)
                    
                    if member != None:
                        await member.send(f"Your ticket has been closed, to reopen it, please create a new one in {guild.name}.")
                
                # Only close the ticket if it's a guild's channel
                if isinstance(interaction.channel, discord.guild.GuildChannel):
                    await interaction.channel.delete()
                    await interaction.response.send_message("Ticket closed.", ephemeral=True)
            
        elif status == "open":
            await interaction.response.send_message("The ticket isn't claimed yet.", ephemeral=True)
 

async def setup(bot):
    """
    Set up the Ticket cog.
    
    Args:
        bot (commands.Bot): The bot instance to add the cog to
    """
    await bot.add_cog(TicketCog(bot))