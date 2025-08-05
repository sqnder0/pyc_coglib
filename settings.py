"""
PyC CogLib Settings Management Module

A flexible JSON-based settings system with dot-notation access and automatic
file synchronization. Provides a centralized configuration system for the
Discord bot and its cogs.

Features:
- Dot-notation path access (e.g., "module.feature.setting")
- Automatic file creation and synchronization
- Per-cog namespacing support
- Discord embed color utilities
- Type-safe default value handling

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

import json
import os
import inspect
from typing import Any
import discord

# Sentinel value to distinguish between None and "not provided"
_sentinel = object()


class Settings():
    """
    A JSON-based settings manager with dot-notation path support.
    
    This class provides a persistent key-value store using JSON files,
    with support for nested dictionaries accessed via dot notation
    (e.g., "database.host" maps to {"database": {"host": value}}).
    
    Attributes:
        filename (str): Path to the JSON settings file
        settings (dict): In-memory representation of the settings
    """
    
    def __init__(self, filename: str):
        """
        Initialize a new Settings instance.
        
        Args:
            filename (str): Path to the JSON file to use for persistence
        """
        self.filename = filename
        self.settings = {}
    
    def setup(self):
        """
        Initialize the settings file and load existing data.
        
        Creates a new JSON file if one doesn't exist, otherwise loads
        the existing settings into memory.
        """
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as file:
                json.dump(self.settings, file)
        else:
            with open(self.filename, "r") as file:
                self.settings = json.load(file)
    
    def save(self):
        """Save the current in-memory settings to the JSON file."""
        with open(self.filename, "w") as file:
            json.dump(self.settings, file, indent=3)
    def put(self, path: str, value):
        """
        Set or overwrite the value at the specified dot-separated path in the settings JSON.
        If any intermediate keys along the path do not exist, they will be created as dictionaries.
        The settings wil automatically be saved to the original JSON file.

        Args:
            path (str): Dot-separated path specifying where to set the value (e.g., "foo.bar.baz").
            value (Any): The value to assign at the given path.

        Returns:
            Any: The value that was set at the specified path.

        Side Effects:
            Modifies the internal JSON structure and persists changes to the settings file.

        Raises:
            ValueError: If an intermediate path segment exists but is not a dictionary,
                        making it impossible to traverse further.
        """
        
        path_list = path.split(".")
        
        current_path = self.settings
        
        for path_segment in path_list[:-1]:
            if path_segment not in current_path:
                current_path[path_segment] = {}
            elif not isinstance(current_path[path_segment], dict):
                raise ValueError
            
            current_path = current_path[path_segment]
        
        last_path = path_list[-1]
        current_path[last_path] = value
        
        self.save()
        
        return value
    
    def get_or_create(self, path: str, default: Any = _sentinel):
        """
        Retrieve the value at a given dot-separated path in the settings JSON file. 
        If the path does not exist, create the necessary structure and assign a default value.

        Args:
            path (str): Dot-separated path within the JSON file (e.g., "foo.bar")
            default (Any, optional): Default value to insert and return if the path does not exist. 
                                    If not provided and the path is missing, KeyError is raised.


        Returns:
            The value found at the path, or the newly created value if the path was missing.

        Side Effects:
            May modify the settings JSON file if the path did not previously exist.
        
        Raises:
            KeyError: If the path does not exist and no default is provided.
            ValueError: If you try to index in a non json value.
        """
        
        path_list = path.split(".")
        
        current_path = self.settings
        
        updated_settings = False
        
        for path_segment in path_list[:-1]:
            if path_segment not in current_path:
                updated_settings = True
                current_path[path_segment] = {}
            elif not isinstance(current_path[path_segment], dict):
                raise ValueError
            
            current_path = current_path[path_segment]
        
        last_path = path_list[-1]
        
        if last_path not in current_path:
            if default == _sentinel:
                raise KeyError
            else:
                updated_settings = True
                current_path[last_path] = default
            
        if updated_settings == True:
            self.save()

        return current_path[last_path]
        
    
    def get_settings_as_dict(self): 
        """
        Get the complete settings dictionary.
        
        Returns:
            dict: The entire settings dictionary
        """
        return self.settings
    
    def get_embed_color(self): 
        """
        Get the configured Discord embed color.
        
        Returns:
            discord.Color: The embed color, defaults to Discord's blurple (#5865F2)
        """
        return discord.Color(int(self.get_or_create("embed.color", "#5865F2").strip().lstrip("#"), 16))

def get_settings():
    """
    Get the global Settings instance (singleton pattern).
    
    Returns:
        Settings: The shared settings instance, creating it if necessary
        
    This function ensures there's only one Settings instance throughout
    the application, initialized with "settings.json" as the backing file.
    """
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = Settings("settings.json")
        get_settings._instance.setup()
    return get_settings._instance

def get_path(path: str):
    """
    Create a namespaced settings path for the calling cog.
    
    Args:
        path (str): The setting path within the cog's namespace
        
    Returns:
        str: A namespaced path in the format "cogname.path"
        
    Example:
        # Called from moderation.py
        get_path("warn_threshold")  # Returns "moderation.warn_threshold"
        
    This function automatically prefixes the provided path with the
    calling file's name (without extension), providing automatic
    namespacing for cog settings.
    """
    
    filename_full = inspect.stack()[1].filename
    filename = os.path.splitext(os.path.basename(filename_full))[0]
    
    return filename.lower() + "." + path