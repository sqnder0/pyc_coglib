"""
PyC CogLib Web Panel Integration Cog

Flask blueprint integration for the web panel interface. Provides the backend
routes and functionality for the web-based bot management interface.

Features:
- Bot status monitoring and display
- Remote bot startup capabilities
- Cross-platform terminal/console launching
- Bot attribute querying with type conversion
- Error handling for offline bot states

This cog works in conjunction with the api.py module to provide a complete
web-based management interface for the Discord bot.

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

from discord.ext import commands
from discord import app_commands
from settings import get_settings, get_path
from flask import render_template
from flask_login import login_required
from flask import Blueprint, jsonify
from typing import Any
import logging
import requests
import subprocess
import platform
import sys
import os

from api import HOST, PORT

SETTINGS = get_settings()
logger = logging.getLogger("main")

class WebPanelCog(commands.Cog):
    """
    Web panel integration cog for Discord bot management.
    
    This cog provides the Discord.py side of the web panel integration,
    primarily serving as a registration point for the Flask blueprint.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the WebPanel cog.
        
        Args:
            bot (commands.Bot): The Discord bot instance
        """
        self.bot = bot

    
webpanel = Blueprint("webapp", __name__)

@webpanel.route("/")
@login_required
def index():
    """
    Main dashboard route for the web panel.
    
    Returns:
        str: Rendered HTML template for the main dashboard
        
    This route gathers bot information including name, status, and cog list
    to display on the main dashboard. Handles offline bot states gracefully.
    """
    
    try:
        bot_data = {
            "name": parse_bot_attribute("user.name")["value"],
            "id": parse_bot_attribute("user.discriminator")["value"],
            "cogs": make_request(f"http://{HOST}:{PORT}/cogs"),
            "status": "online"
        }
    except:
        bot_data = {
            "name": "Offline",
            "id": "",
            "cogs": [],
            "status": "offline"
        }

        
    return render_template("index.html", title=bot_data["name"], bot=bot_data)

@webpanel.route("/start")
@login_required
def start_bot():
    """
    Start the bot in a new terminal/console window.
    
    Returns:
        tuple: JSON response with success status and HTTP code
        
    This route attempts to start the bot in a new terminal window
    based on the detected operating system:
    - Linux: Uses gnome-terminal or xterm as fallback
    - Windows: Uses cmd with start command
    - macOS: Uses AppleScript to open Terminal
    
    The bot is started using the current Python interpreter to ensure
    environment compatibility.
    """
    bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot.py'))
    bot_dir = os.path.dirname(bot_path)
    python_exec = sys.executable  # Current Python interpreter path
    system = platform.system()

    try:
        if system == "Linux":
            # Try gnome-terminal, fallback to xterm
            try:
                subprocess.Popen([ 'gnome-terminal', '--', python_exec, bot_path ])
            except FileNotFoundError:
                subprocess.Popen([ 'xterm', '-e', f'{python_exec} {bot_path}' ])
        elif system == "Windows":
            # Use 'start' command to open new cmd window
            cmd_args = ['start', '', 'cmd', '/k', python_exec, bot_path]
            cmd = subprocess.list2cmdline(cmd_args)
            print(f'Running command: {cmd}')
            subprocess.Popen(cmd, shell=True, cwd=bot_dir)
        elif system == "Darwin":  # macOS
            applescript = f'''
            tell application "Terminal"
                do script "{python_exec} {bot_path}"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', applescript])
        else:
            return jsonify({"Success": False, "Error": "Unsupported OS"}), 400

        return jsonify({"Success": True}), 200

    except Exception as e:
        return jsonify({"Success": False, "Error": str(e)}), 500

def parse_bot_attribute(attribute: str, return_type: type=str, round_to=None) -> dict[str, Any]:
    """
    Parse and convert a bot attribute from the API.
    
    Args:
        attribute (str): Dot-separated path to the bot attribute
        return_type (type): Expected return type for conversion
        round_to (int, optional): Number of decimal places for rounding
        
    Returns:
        dict[str, Any]: Dictionary containing 'value' and 'count' keys
        
    This function queries the bot API for a specific attribute and handles
    type conversion and error cases. It provides a structured response
    format for consistent handling in the web interface.
    """
    response = requests.get(f"http://{HOST}:{PORT}/bot-attribute", params={"attribute": attribute}, timeout=(0.3, 1.0))
    
    return_dict: dict[str, Any] = {"value": None, "count": None}
    
    if response.status_code == 200:
        data = response.json()
        
        if "value" in data:
            value = data["value"]
            
            if value == None:
                logger.warning(f"Couldn't fetch value from {data}")
                return return_dict
            else:
                try:
                    converted_value = return_type(value)
                    if round_to: converted_value = round(converted_value, round_to)
                    
                    return_dict["value"] = converted_value
                    
                    if "count" in data:
                        return_dict["count"] = int(data["count"]) if data["count"] else None
                    
                    return return_dict
                    
                except ValueError:
                    print(f"Expected type {return_type} for value 'ping' but got: {type(value)}")
                    logger.error(f"Expected type {return_type} for value 'ping' but got: {type(value)}")
                    return return_dict
        
        else:
            print(f"Error: {data.get('error', 'Unknown error')}")
            logger.error(f"Error: {data.get('error', 'Unknown error')}")
            return return_dict
            
    else:
        logger.error(f"HTTP error: {response.status_code}")
        return return_dict

def make_request(request: str):
    """
    Make a GET request to the specified URL.
    
    Args:
        request (str): The URL to make a request to
        
    Returns:
        dict: JSON response if successful, error dict if failed
        
    This is a simple wrapper around requests.get that provides
    consistent error handling for API communication.
    """
    response = requests.get(request)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code}
        
        
async def setup(bot_arg):
    """
    Set up the WebPanel cog.
    
    Args:
        bot_arg (commands.Bot): The bot instance to add the cog to
        
    This function registers both the cog and sets up the global bot reference
    for use in the Flask blueprint routes.
    """
    global bot
    bot = bot_arg
    await bot_arg.add_cog(WebPanelCog(bot_arg))