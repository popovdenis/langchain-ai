from __future__ import annotations

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from config.settings import Settings


class StudentSQLAgent:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.db = SQLDatabase.from_uri(Settings.postgres_uri())
        self.llm = ChatOpenAI(
            temperature=0,
            model=Settings.OPENAI_API_MODEL,
            api_key=Settings.OPENAI_API_KEY
        )
        self.agent = create_sql_agent(
            llm=self.llm,
            toolkit=SQLDatabaseToolkit(db=self.db, llm=self.llm),
            verbose=debug
        )

    def run_analysis(self, student_email: str, week_from: int, week_to: int) -> str:
        prompt = self._build_prompt(student_email, week_from, week_to)

        if self.debug:
            print("Prompt sent to GPT:\n" + prompt)
            print("-" * 80)

        result = self.agent.invoke(prompt)

        if self.debug:
            if isinstance(result, dict) and "output" in result:
                print("\nFinal result from GPT:\n" + result["output"])
            else:
                print("\nUnexpected result format:\n", result)
            print("-" * 80)

        return result

    def _build_prompt(self, email: str, week_from: int, week_to: int) -> str:
        return f"""
You are an educational data analyst AI.

Given the student email '{email}' and the week range {week_from} to {week_to}, do the following:
1. Look up the user ID by email from the 'users' table.
2. Select all records for this user from 'student_metrics' where week is between {week_from} and {week_to}.
3. For each metric:
   - homework_submitted (binary)
   - homework_on_time (binary)
   - homework_score (0–9)
   - attendance (0–1)
   - student_participation (0–1)
   - teacher_participation (0–1)
   - silence (0–1)
   - test_score (0–9)

Calculate the average values and round them reasonably.

Then, based on a scoring system:
- green zone: total score > 75
- yellow zone: 46–75
- red zone: ≤ 45

Return:
- summary table of averages per metric
- total score
- motivation zone value in percent
- a motivational message in English
"""