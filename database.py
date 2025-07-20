import sqlite3
import logging

logger = logging.getLogger("main")

class Database():
    def __init__(self, filename: str):
        try:
            self.connection = sqlite3.connect(filename)
            self.cursor = self.connection.cursor()
            
            logger.debug("Database initialized!")
            
        except sqlite3.Error as error:
            logger.error("Error occurred: ", error)
    
    def execute(self, statement: str, *args):
        self.cursor.execute(statement, args)
        result = self.cursor.fetchall()
        
        return result
    
    def close(self):
        if self.connection:
            self.connection.close()
            logger.debug("Database closed")
        else:
            logger.debug("No connection found")
        

def get_database():
    if not hasattr(get_database, "_instance"):
        get_database._instance = Database("sqlite.db")
    return get_database._instance