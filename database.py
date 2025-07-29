import sqlite3
import logging
import os

logger = logging.getLogger("main")

class Database():
    def __init__(self, filename: str):
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
        self.cursor.execute(statement, args)
        result = self.cursor.fetchall()
        
        return result
    
    def commit(self):
        """Save changes to disk."""
        if self.connection:
            self.connection.commit()
            logger.debug("Database changes saved")
    
    def close(self):
        """Close & save the database"""
        if self.connection:
            self.commit()
            self.connection.close()
            logger.debug("Database closed")
        else:
            logger.debug("No connection found")
        

def get_database():
    if not hasattr(get_database, "_instance"):
        get_database._instance = Database("sqlite.db")
    return get_database._instance