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
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
webpanel = Blueprint("webapp", __name__)

@webpanel.route("/")
@login_required
def index():
    
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
    response = requests.get(request)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code}
        
        
async def setup(bot_arg):
    global bot
    bot = bot_arg
    await bot_arg.add_cog(WebPanelCog(bot_arg))