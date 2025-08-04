"""
The API for ICP between the bot and the web panel.
This file is only loaded when you have the webpanel cog installed.
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
    global HOST
    HOST = host

def set_port(port: int):
    global PORT
    PORT = port

def set_bot(bot: commands.Bot):
    global BOT
    BOT = bot

def get_server():
    return server
    
F = TypeVar("F", bound=Callable)

def bot_check(func: F) -> F:
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
    assert BOT != None
    return BOT.latency

@bot_check
@api.get("/bot-attribute")
async def get_bot_attribute(attribute: str):
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

        return {"cog_name": cog_name, "registered": False}, 20

@bot_check
@api.get("/logs")
def get_logs():
    try:
        with open(LOG_FILENAME, "r") as file:
            lines = file.readlines()[-50:]
    except FileNotFoundError:
        return {"error": "Log file not found"}, 404
    
    return {"lines": lines}, 200

@bot_check
@api.get("/stop")
async def shutdown():
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
    return Response(status_code=200)
    