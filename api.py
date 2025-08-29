"""
PyC CogLib Web API Module

FastAPI-based REST API for inter-process communication between the Discord bot
and the optional web panel. Provides endpoints for bot management, monitoring,
and remote control operations.

Features:
- Bot status and attribute monitoring
- Cog management (load/unload/list)
- Log file access
- Remote shutdown capabilities
- Heartbeat monitoring
- Automatic bot availability checking

This module is only loaded when the webpanel cog is installed and provides
the backend API that the web interface communicates with.

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""
import os
import uvicorn
import functools
import inspect
import asyncio
from database import get_database
from logging import Logger
from datetime import datetime
from collections.abc import Sized, Iterable
from fastapi import FastAPI, HTTPException, Response
from discord.ext import commands
from typing import TypeVar, Callable

# Define the api
api = FastAPI()

# Configuration for the api
HOST = "localhost"
PORT = 5566

# Other global variables
LOG_FILENAME =  f"""logs/{datetime.now().strftime("%d-%m-%Y")}.log"""
BOT = None
DATABASE = get_database()
logger = Logger("main")

# Create api config and create the api server
config = uvicorn.Config(api, host=HOST, port=PORT)
server = uvicorn.Server(config)

def set_host(host: str):
    """
    Configure the API server host address.
    
    Args:
        host (str): The host address to bind the API server to
    """
    global HOST
    HOST = host

def set_port(port: int):
    """
    Configure the API server port.
    
    Args:
        port (int): The port number to bind the API server to
    """
    global PORT
    PORT = port

def set_bot(bot: commands.Bot):
    """
    Set the Discord bot instance for API operations.
    
    Args:
        bot (commands.Bot): The Discord bot instance to manage
    """
    global BOT
    BOT = bot

def get_server():
    """
    Get the configured uvicorn server instance.
    
    Returns:
        uvicorn.Server: The configured server ready to run
    """
    return server
    
F = TypeVar("F", bound=Callable)

def bot_check(func: F) -> F:
    """
    Decorator that ensures the bot instance is available before executing API endpoints.
    
    Args:
        func: The API endpoint function to wrap
        
    Returns:
        The wrapped function that checks for bot availability
        
    Raises:
        HTTPException: 404 error if the bot instance is not set
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if BOT == None:
            raise HTTPException(status_code=404, detail=f"Bot isn't set yet.")
        else:
            return await func(*args, **kwargs)
    return wrapper  # type: ignore

@bot_check
@api.get("/latency")
async def latency():
    """
    Get the bot's current latency to Discord's servers.
    
    Returns:
        float: The bot's latency in seconds
    """
    assert BOT != None
    return BOT.latency

@bot_check
@api.get("/bot-attribute")
async def get_bot_attribute(attribute: str):
    """
    Get a specific attribute from the bot instance using dot notation.
    
    Args:
        attribute (str): Dot-separated path to the desired attribute (e.g., "user.name")
        
    Returns:
        dict: Contains the attribute value, its string representation, and count if applicable
        
    Raises:
        HTTPException: 404 error if the attribute path is not found
        
    This endpoint supports method calls and provides special handling for
    sized and iterable objects to include count information.
    """
    obj = BOT
    try:
        for attr in attribute.split("."):
            obj = getattr(obj, attr)
            
        if callable(obj):
            obj = obj()
            if inspect.isawaitable(obj):
                obj = await obj
        
        # Handle count
        if isinstance(obj, Sized):
            count = len(obj)
        elif isinstance(obj, Iterable):
            obj = list(obj)  # Convert to list so we can measure its length
            count = len(obj)
        else:
            count = None
        
        response = {"attribute": attribute,
                    "value": str(obj),
                    "count": count}
             
        return response
    except AttributeError:
        raise HTTPException(status_code=404, detail=f"Attribute '{attribute}' not found")

@bot_check
@api.get("/cogs")
async def get_bot_cogs():
    """
    Get information about all available cogs and their current status.
    
    Returns:
        dict: Contains a list of cogs with their names and active status
        
    This endpoint scans the cogs/ directory for Python files and compares
    them against currently loaded extensions to determine which cogs are
    active and which are available but not loaded.
    """
    assert BOT
    
    cog_path = os.path.join(os.path.dirname(__file__), "cogs/")
    
    all_cogs = []
    
    active_files = set()

    for cog_instance in BOT.cogs.values():
        file_path = inspect.getfile(cog_instance.__class__)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        active_files.add(file_name)
    
    for cog in os.listdir(cog_path):
        if cog.endswith(".py"):
            cog_dict = {}
            cog_dict["name"] = os.path.splitext(cog)[0]
            
            cog_dict["active"] = cog_dict["name"] in active_files
            
            all_cogs.append(cog_dict)
    
    return {"cogs": all_cogs}

@bot_check
@api.get("/toggle_cog")
async def toggle_cog(cog: str, register: bool):
    """
    Load or unload a specific cog.
    
    Args:
        cog (str): The name of the cog to toggle
        register (bool): True to load the cog, False to unload it
        
    Returns:
        tuple: A tuple containing response data and HTTP status code
        
    This endpoint provides dynamic cog management, allowing cogs to be
    loaded and unloaded without restarting the bot.
    """
    assert BOT
    
    cog_name = f"cogs.{cog}"
    cog_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cogs")
    cog_path = os.path.join(cog_dir, f"{cog}.py")

    if not os.path.exists(cog_path):
        return {"error": "Cog not found"}, 404

    if register:
        # Load only if not loaded
        if cog_name not in BOT.extensions:
            try:
                await BOT.load_extension(cog_name)
            except Exception as e:
                return {"error": f"Failed to load cog: {e}"}, 500
            
        return {"cog_name": cog_name, "registered": True}, 200
    else:
        # Unload only if loaded
        if cog_name in BOT.extensions:
            try:
                await BOT.unload_extension(cog_name)
            except Exception as e:
                return {"error": f"Failed to unload cog: {e}"}, 500

        return {"cog_name": cog_name, "registered": False}, 200

@bot_check
@api.get("/logs")
def get_logs():
    """
    Retrieve the last 50 lines from today's log file.
    
    Returns:
        tuple: A tuple containing log lines and HTTP status code
        
    This endpoint provides access to recent log entries for debugging
    and monitoring purposes. Returns a 404 if the log file doesn't exist.
    """
    try:
        with open(LOG_FILENAME, "r") as file:
            lines = file.readlines()[-50:]
    except FileNotFoundError:
        return {"error": "Log file not found"}, 404
    
    return {"lines": lines}, 200

@bot_check
@api.get("/stop")
async def shutdown():
    """
    Gracefully shutdown the bot and API server.
    
    Returns:
        Response: HTTP 200 OK response
        
    This endpoint triggers a graceful shutdown sequence:
    1. Saves and closes the database
    2. Closes the bot connection
    3. Exits the process after a brief delay
    
    The delay allows the HTTP response to be sent before process termination.
    """
    assert BOT
    logger.debug("Shutdown detected, saving database...")
    DATABASE.close()

    logger.info("Closing bot...")
    await BOT.close()
    
    async def delayed_exit():
        await asyncio.sleep(0.5)
        os._exit(0)
    
    # Return 200 ok, and then exit the process
    asyncio.create_task(delayed_exit())
    return Response(status_code=200)

@bot_check
@api.get("/heartbeat")
def heartbeat():
    """
    Simple health check endpoint.
    
    Returns:
        Response: HTTP 200 OK response if the bot is running
        
    This endpoint can be used to verify that the API server and bot
    are both running and responsive.
    """
    return Response(status_code=200)
    