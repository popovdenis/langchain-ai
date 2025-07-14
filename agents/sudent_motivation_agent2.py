import os
import ast
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from config.settings import Settings

class StudentMotivationAgent2:
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.llm = ChatOpenAI()
        self.db = SQLDatabase.from_uri(Settings.mysql_uri())
        self.metric_weights = {
            "homework_submitted": float(os.getenv("WEIGHT_HOMEWORK_SUBMITTED", 0.1)),
            "homework_on_time": float(os.getenv("WEIGHT_HOMEWORK_ON_TIME", 0.1)),
            "homework_score": float(os.getenv("WEIGHT_HOMEWORK_SCORE", 0.2)),
            "attendance": float(os.getenv("WEIGHT_ATTENDANCE", 0.2)),
            "student_participation": float(os.getenv("WEIGHT_STUDENT_PARTICIPATION", 0.1)),
            "teacher_participation": float(os.getenv("WEIGHT_TEACHER_PARTICIPATION", 0.1)),
            "silence": float(os.getenv("WEIGHT_SILENCE", 0.1)),
            "test_score": float(os.getenv("WEIGHT_TEST_SCORE", 0.1)),
        }

    def build_sql_prompt(self, email: str, week_from: int, week_to: int) -> str:
        return f"""
Write an SQL query that:
1. Finds the ID of the student with email = '{email}'
2. Selects all student_metrics where week between {week_from} and {week_to} and user_id matches.
3. Calculates AVG for each metric (exclude id, user_id, week).
Only return a valid SQL query.
""".strip()

    def get_schema(self, _=None):
        return self.db.get_table_info()

    def run_analysis(self, email: str, week_from: int, week_to: int) -> list[dict]:
        start_time = time.time()
        # Step 1: Generate SQL
        sql_prompt = ChatPromptTemplate.from_template("""
Based on the table schema below, write an SQL query that would answer the user's question:
{schema}

Question: {question}
SQL Query:
""")
        sql_chain = (
            RunnablePassthrough.assign(schema=self.get_schema)
            | sql_prompt
            | self.llm.bind(stop="\SQL Result:")
            | StrOutputParser()
        )

        question = self.build_sql_prompt(email, week_from, week_to)
        sql_query = sql_chain.invoke({"question": question})

        if self.debug:
            print("Generated SQL:\n", sql_query)

        # Step 2: Run SQL
        try:
            result_str = self.db.run(sql_query)
        except Exception as e:
            raise ValueError(f"Database error: {e}")

        if self.debug:
            print("Raw SQL result:\n", result_str)

        # Step 3: Parse & analyse
        try:
            parsed = ast.literal_eval(result_str)[0]
        except Exception as e:
            raise ValueError(f"Result parsing failed: {e}")

        if self.debug:
            print("Parse result:\n", parsed)

        metrics_res = self._analyse_metrics(parsed)

        elapsed_time = time.time() - start_time
        if self.debug:
            print(f"\nFull time: {elapsed_time:.2f} seconds")

        return metrics_res

    def _analyse_metrics(self, parsed_result: list[float]) -> list[dict]:
        metric_order = list(self.metric_weights.keys())

        if self.debug:
            print("Metrics result:\n", parsed_result)
            print("Metrics order:\n", metric_order)

        summary = []
        subtotal = 0.0
        min_metric = None
        min_value = None

        for metric, value in zip(metric_order, parsed_result):
            summary.append({
                "label": metric.replace("_", " ").title(),
                "value": round(value * 100, 2)
            })
            weighted = value * self.metric_weights[metric]
            subtotal += weighted

            if min_value is None or value < min_value:
                min_value = value
                min_metric = metric

        total_score = round(subtotal * 100, 2)
        motivation_zone = (
            "Red" if total_score <= 45 else
            "Yellow" if total_score <= 75 else
            "Green"
        )

        # Step 4: LLM motivational message
        message_prompt = ChatPromptTemplate.from_template("""
The student's weakest metric is: {metric}.

Write a motivational message (at least 15 tokens) that helps the student improve in this area.
Be optimistic, specific, and helpful. Only return the message text.
""")
        msg_chain = message_prompt | self.llm | StrOutputParser()
        motivation_message = msg_chain.invoke({
            "metric": min_metric.replace("_", " ")
        })

        if self.debug:
            print("Motivation result:\n", motivation_message)

        summary.append({"label": "Subtotal", "value": round(subtotal, 4)})
        summary.append({"label": "Total Score", "value": f"{total_score}%"})
        summary.append({"label": "Motivation Zone", "value": motivation_zone})
        summary.append({"label": "Motivational Message", "value": motivation_message.strip()})
        return summary