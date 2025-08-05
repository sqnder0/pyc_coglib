"""
PyC CogLib Database Management Module

A lightweight SQLite wrapper providing easy database operations for the
Discord bot. Features automatic database creation, connection management,
and proper resource cleanup.

This module provides a simple interface for SQL operations while handling
connection lifecycle and error management automatically.

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

import sqlite3
import logging
import os

logger = logging.getLogger("main")

class Database():
    """
    A lightweight SQLite database wrapper with automatic connection management.
    
    This class provides a simple interface for executing SQL statements
    while handling connection setup, error logging, and proper resource cleanup.
    
    Attributes:
        connection (sqlite3.Connection): The SQLite database connection
        cursor (sqlite3.Cursor): The database cursor for executing statements
    """
    
    def __init__(self, filename: str):
        """
        Initialize a new Database instance.
        
        Args:
            filename (str): Path to the SQLite database file
            
        Creates the database file if it doesn't exist and establishes
        a connection. Logs success or failure appropriately.
        """
        # Create the db if not exists.
        if not os.path.exists(filename):
            with open(filename, "x") as file:
                file.write("")
        
        try:
            self.connection = sqlite3.connect(filename)
            self.cursor = self.connection.cursor()
            
            logger.debug("Database initialized!")
            
        except sqlite3.Error as error:
            logger.error("Error occurred: ", error)
    
    def execute(self, statement: str, *args):
        """Execute an sql statement on the db

        Args:
            statement (str): The statement you want to execute, use "?" as placeholder.

        Returns:
            list[tuple[]]: Every tuple is a row, every item in the tuple is a column.
        """
        
        # Only pass args if there are args.
        if args:
            self.cursor.execute(statement, args)
        else:
            self.cursor.execute(statement)
        
        result = self.cursor.fetchall()
        
        return result
    
    def commit(self):
        """Save changes to disk."""
        if self.connection:
            self.connection.commit()
            logger.debug("Database changes saved")
    
    def close(self):
        """
        Close the database connection and save any pending changes.
        
        This method ensures all changes are committed before closing
        the connection. Safe to call multiple times.
        """
        if self.connection:
            self.commit()
            self.connection.close()
            logger.debug("Database closed")
        else:
            logger.debug("No connection found")
        

def get_database():
    """
    Get the global Database instance (singleton pattern).
    
    Returns:
        Database: The shared database instance, creating it if necessary
        
    This function ensures there's only one Database instance throughout
    the application, initialized with "sqlite.db" as the database file.
    """
    if not hasattr(get_database, "_instance"):
        get_database._instance = Database("sqlite.db")
    return get_database._instance