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

Each record contains the following metrics (all values are percentages in decimal format):

- homework_submitted (0–1)
- homework_on_time (0–1)
- homework_score (0–1)
- attendance (0–1)
- student_participation (0–1)
- teacher_participation (0–1)
- silence (0–1) — represents pauses during the lesson, not inverse of speech
- test_score (0–1)

Steps:

1. For each metric, calculate the average across the selected weeks.
2. Multiply each average by its predefined weight (stored in the system).
3. Exclude the 'silence' metric from subtotal and motivation zone calculation.
4. Sum the remaining weighted averages into a subtotal (between 0 and 1).
5. Multiply subtotal by 100 to get total score (0–100).
6. Identify the weakest metric (lowest average), excluding 'silence'.
7. Determine the motivation zone:
   - Red: ≤ 45
   - Yellow: 46–75
   - Green: > 75

Return the following:

- Summary table of averages per metric (including silence)
- Subtotal (decimal)
- Total score (percentage)
- Motivation zone (Red / Yellow / Green)
- Motivational message in English that includes advice on improving the weakest metric (excluding silence)
"""