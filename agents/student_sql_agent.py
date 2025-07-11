from __future__ import annotations

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from config.settings import Settings
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

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
            handle_parsing_errors=True,
            verbose=debug
        )

    def run_analysis(self, student_email: str, week_from: int, week_to: int) -> list[dict]:
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

        return self.validate_and_extract_metrics(result)

    def validate_and_extract_metrics(self, result: dict) -> list[dict]:
        if not isinstance(result, dict) or "output" not in result:
            raise ValueError("Invalid result: missing 'output'")

        raw_output = result["output"]
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

Return ONLY valid JSON:

- summary: Summary table of averages per metric
- subtotal: Subtotal (decimal)
- total_score: Total score (percentage)
- motivation_zone: Motivation zone (Red / Yellow / Green)
- motivation_message: Motivational message in English that includes advice on improving the weakest metric
"""