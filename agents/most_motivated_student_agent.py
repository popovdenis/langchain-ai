from __future__ import annotations

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_openai import ChatOpenAI
from config.settings import Settings


class MostMotivatedStudentAgent:
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

    def run_analysis(self, week_from: int, week_to: int) -> str:
        prompt = self._build_prompt(week_from, week_to)

        if self.debug:
            print("Prompt sent to GPT:\n" + prompt)
            print("-" * 80)

        result = self.agent.invoke({"input": prompt})

        if self.debug:
            print("\nFinal result from GPT:\n" + result["output"])
            print("-" * 80)

        return result["output"]

    def _build_prompt(self, week_from: int, week_to: int) -> str:
        return f"""
You are a data analyst AI.

Your task is to identify the **most motivated** student based on their average scores over weeks {week_from} to {week_to}.

Use data from:
- `users` table (id, name, email)
- `student_metrics` table (student_id, week, homework_submitted, homework_on_time, homework_score, attendance, student_participation, teacher_participation, silence, test_score)

Steps:
1. Join `users` and `student_metrics` on `users.id = student_metrics.student_id`.
2. Filter rows where `week` is between {week_from} and {week_to}.
3. Group by student and compute average for each metric.
4. Calculate total motivation score:
   - homework_submitted (0/1)
   - homework_on_time (0/1)
   - homework_score (0–9)
   - attendance (0–1)
   - student_participation (0–1)
   - teacher_participation (0–1)
   - silence (0–1, reverse contributes negatively)
   - test_score (0–9)
5. Rank by total score descending.
6. Return:
   - student name and email
   - average values
   - total score
   - motivation zone:
     - Green: > 75
     - Yellow: 46–75
     - Red: ≤ 45
   - motivational comment in English.
"""