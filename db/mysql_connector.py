from langchain.utilities import SQLDatabase
from config.settings import Settings

def get_mysql_connection() -> SQLDatabase:
    return SQLDatabase.from_uri(Settings.mysql_uri())