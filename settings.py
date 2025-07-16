import json
import os
import inspect
from typing import Any
import discord

_sentinel = object()


class Settings():
    def __init__(self, filename: str):
        self.filename = filename
        self.settings = {}
    
    def setup(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as file:
                json.dump(self.settings, file)
        else:
            with open(self.filename, "r") as file:
                self.settings = json.load(file)
    
    def save(self):
        """Save this class' settings to their json file."""
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
        
    
    def get_settings_as_dict(self): return self.settings
    
    def get_embed_color(self): return discord.Color(int(self.get_or_create("embed.color", "#5865F2").strip().lstrip("#"), 16))
        

def get_settings():
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = Settings("settings.json")
        get_settings._instance.setup()
    return get_settings._instance

def get_path(path: str):
    """Prefix a path with the cogs name

    Args:
        path (str): the path inside the cogs config.
    """
    
    filename_full = inspect.stack()[1].filename
    filename = os.path.splitext(os.path.basename(filename_full))[0]
    
    return filename.lower() + "." + path