import logging
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

from config.settings import Settings
from db.postgree_connector import get_postgres_connection


class MostMotivatedStudentAgent:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.db: SQLDatabase = get_postgres_connection()
        self.llm = ChatOpenAI(temperature=0, model=Settings.OPENAI_API_MODEL, streaming=False)

        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            verbose=debug,
            agent_type="openai-tools",
        )

    def run_analysis(self, week_from: int, week_to: int) -> str:
        prompt = f"""
        You are an educational data analyst AI.

        Find the most motivated student in the table 'student_metrics'
        by calculating the average score across these metrics:

        - homework_submitted (0–1)
        - homework_on_time (0–1)
        - homework_score (0–1)
        - attendance (0–1)
        - student_participation (0–1)
        - test_score (0–1)

        For each user:
        1. Select records between weeks {week_from} and {week_to}
        2. Calculate the average value of each metric
        3. Normalise scores (if needed) to a 0–100 scale
        4. Compute total average motivation score
        5. Identify the student with the **highest total average score**
        6. Return:
            - email
            - total score
            - motivation zone:
                - Red (≤ 45)
                - Yellow (46–75)
                - Green (> 75)
            - motivational message in English
        """

        if self.debug:
            print("\n[DEBUG] Sending prompt to SQL agent:\n" + prompt + "\n")

        result = self.agent.run(prompt)

        if self.debug:
            print("\n[DEBUG] Agent response:\n" + result + "\n")

        return result