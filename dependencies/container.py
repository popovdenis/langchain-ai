from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
import mysql.connector
from config.settings import Settings

class DependencyContainer:
    """Singleton-like container for shared services."""

    def __init__(self):
        self._llm = None
        self._db = None
        self._mydb = None

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                api_key=Settings.OPENAI_API_KEY,
                model=Settings.OPENAI_API_MODEL
            )
        return self._llm

    @property
    def sql_db(self) -> SQLDatabase:
        if self._db is None:
            self._db = SQLDatabase.from_uri(Settings.mysql_uri())
        return self._db

    @property
    def mysql_connection(self):
        if self._mydb is None:
            self._mydb = mysql.connector.connect(
                host=Settings.MYSQL_HOST,
                user=Settings.MYSQL_USER,
                password=Settings.MYSQL_PASSWORD,
                database=Settings.MYSQL_DB
            )
        return self._mydb

container = DependencyContainer()