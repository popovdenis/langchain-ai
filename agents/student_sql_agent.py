from __future__ import annotations

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from config.settings import Settings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from sqlalchemy import create_engine
from langchain_core.messages import AIMessage

# from langchain.cache import InMemoryCache
# from langchain.globals import set_llm_cache
# set_llm_cache(InMemoryCache())  # disable cache

class StudentSQLAgent:
    def __init__(self, debug: bool = False):
        self.debug = debug

        custom_table_info = {
            "users": """
                     CREATE TABLE users
                     (
                         id    SERIAL PRIMARY KEY,
                         email VARCHAR(255) UNIQUE
                     );
                     """,
            "student_metrics": """
                               CREATE TABLE student_metrics
                               (
                                   id                    SERIAL PRIMARY KEY,
                                   user_id               INTEGER REFERENCES users (id),
                                   week                  INTEGER          NOT NULL,
                                   homework_score        DOUBLE PRECISION NOT NULL,
                                   attendance            DOUBLE PRECISION NOT NULL,
                                   student_participation DOUBLE PRECISION NOT NULL,
                                   teacher_participation DOUBLE PRECISION NOT NULL,
                                   silence               DOUBLE PRECISION NOT NULL,
                                   test_score            DOUBLE PRECISION NOT NULL,
                                   homework_submitted    DOUBLE PRECISION NOT NULL,
                                   homework_on_time      DOUBLE PRECISION NOT NULL
                               );
                               """
        }

        self.db = SQLDatabase(
            engine=create_engine(Settings.postgres_uri()),
            include_tables=["users", "student_metrics"],
            sample_rows_in_table_info=1,
            custom_table_info=custom_table_info,
            lazy_table_reflection=True,
        )
        self.llm = ChatOpenAI(
            temperature=0,
            model=Settings.OPENAI_API_MODEL,
            api_key=Settings.OPENAI_API_KEY,
            streaming=False,
            cache=True,
        )
        self.agent = create_sql_agent(
            llm=self.llm,
            toolkit=SQLDatabaseToolkit(db=self.db, llm=self.llm),
            handle_parsing_errors=False,
            verbose=self.debug,
            cache=True,
        )

    def run_analysis(self, student_email: str, week_from: int, week_to: int) -> list[dict]:
        prompt = self._build_prompt(student_email, week_from, week_to)

        if self.debug:
            print("Prompt sent to GPT:\n" + prompt)
            print("-" * 80)

        try:
            result = self.agent.invoke(prompt)
        except Exception as e:
            print("Error while invoke:", e)
            raise ValueError("Invalid agent invoke")

        if self.debug:
            if isinstance(result, dict) and "output" in result:
                print("\nFinal result from GPT:\n" + result["output"])
            else:
                print("\nUnexpected result format:\n", result)
            print("-" * 80)

        return self.validate_and_extract_metrics(result)

    def validate_and_extract_metrics(self, result: dict) -> list[dict]:
        if not isinstance(result, dict) or "output" not in result:
            raise ValueError("Invalid result: missing 'output'")

        raw_output = result["output"]

        if self.debug:
            print("Output from GPT:\n" + raw_output)
            print("-" * 80)

        if not isinstance(raw_output, str):
            raise ValueError("Invalid output: must be a string")

        try:
            message = AIMessage(raw_output)
            output_parser = JsonOutputParser()
            parsed = output_parser.invoke(message)
        except OutputParserException as e:
            raise ValueError(f"AI output could not be parsed as JSON: {str(e)}")

        required_keys = ["summary", "subtotal", "total_score", "motivation_zone", "motivation_message"]
        missing_keys = [key for key in required_keys if key not in parsed or parsed[key] in [None, "", {}]]

        if missing_keys:
            raise ValueError(f"Missing or empty keys in AI output: {', '.join(missing_keys)}")

        result_data = []

        # metrics
        for metric, value in parsed["summary"].items():
            result_data.append({
                "label": metric.replace("avg_", "").replace("_", " ").title(),
                "value": round(value, 4)
            })

        # other parameters
        result_data.append({"label": "Subtotal", "value": round(parsed["subtotal"], 4)})
        result_data.append({"label": "Total Score", "value": f"{round(parsed['total_score'], 2)}%"})
        result_data.append({"label": "Motivation Zone", "value": parsed["motivation_zone"]})
        result_data.append({"label": "Motivational Message", "value": parsed["motivation_message"]})
        # result_data.append({"label": "Parsed result", "value": self.get_debug_log()})

        return result_data

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
- test_score (0–1)

Steps:

1. For each metric, calculate the average across the selected weeks.
2. Multiply each average by its predefined weight (stored in the system).
3. Sum the remaining weighted averages into a subtotal (between 0 and 1).
4. Multiply subtotal by 100 to get total score (0–100).
5. Identify the weakest metric (lowest average).
6. Determine the motivation zone:
   - Red: ≤ 45
   - Yellow: 46–75
   - Green: > 75

Return ONLY valid JSON with the following fields:

- summary: Summary table of averages per metric
- subtotal: Subtotal (decimal)
- total_score: Total score (percentage)
- motivation_zone: Motivation zone (Red / Yellow / Green)
- motivation_message: Motivational message in English that helps the student improve their weakest metric.The message should be practical, optimistic, and contain at least 15 tokens.
"""