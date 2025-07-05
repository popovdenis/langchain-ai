from langchain.utilities import SQLDatabase
from config.settings import Settings

def get_postgres_connection() -> SQLDatabase:
    return SQLDatabase.from_uri(Settings.postgres_uri())