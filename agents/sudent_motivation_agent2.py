import os
import ast
import time
import logging
from datetime import datetime

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
            "homework_submitted": float(getattr(Settings, "WEIGHT_HOMEWORK_SUBMITTED", 0.1)),
            "homework_on_time": float(getattr(Settings, "WEIGHT_HOMEWORK_ON_TIME", 0.1)),
            "homework_score": float(getattr(Settings, "WEIGHT_HOMEWORK_SCORE", 0.2)),
            "attendance": float(getattr(Settings, "WEIGHT_ATTENDANCE", 0.2)),
            "student_participation": float(getattr(Settings, "WEIGHT_STUDENT_PARTICIPATION", 0.1)),
            "teacher_participation": float(getattr(Settings, "WEIGHT_TEACHER_PARTICIPATION", 0.1)),
            # "silence": float(getattr(Settings, "WEIGHT_SILENCE", 0.1)),
            "test_score": float(getattr(Settings, "WEIGHT_TEST_SCORE", 0.1)),
        }

        self._configure_logger()

    def _configure_logger(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"logging_{today}.log")

        # Check rights
        if os.path.exists(log_file) and not os.access(log_file, os.W_OK):
            raise PermissionError(f"No write permission to existing log file: {log_file}")
        if not os.access(log_dir, os.W_OK):
            raise PermissionError(f"No write permission to directory: {log_dir}")

        logging.basicConfig(
            filename=log_file,
            filemode='a',
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        if self.debug:
            logging.getLogger().addHandler(logging.StreamHandler())

    def build_sql_prompt(self, email: str, week_from: int, week_to: int) -> str:
        return f"""
Write an SQL query that:
1. Finds the ID of the student with email = '{email}'
2. Selects all student_metrics where week between {week_from} and {week_to} and user_id matches.
3. Calculates AVG for each of these metrics: homework_submitted, homework_on_time, homework_score, attendance, student_participation, teacher_participation, test_score.
4. Return values of these metrics only. Exclude id, week.
Only return a valid SQL query.
""".strip()

    def get_schema(self, _=None):
        try:
            return self.db.get_table_info()
        except Exception as e:
            logging.error(f"Failed to fetch schema: {e}")
            raise

    def run_analysis(self, email: str, week_from: int, week_to: int) -> list[dict]:
        start_time = time.time()
        logging.info("Start analysis")
        try:
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

            logging.info("Start generating SQL prompt")
            question = self.build_sql_prompt(email, week_from, week_to)
            logging.info(f"Question:\n{question}")

            logging.info("Start invoke question")
            sql_query = sql_chain.invoke({"question": question})
            logging.info(f"Generated SQL:\n{sql_query}")

            # Step 2: Execute SQL
            try:
                logging.info("Start executing SQL query")
                result_str = self.db.run(sql_query)
            except Exception as e:
                logging.error(f"Database query failed: {e}")
                raise

            logging.info(f"Raw SQL result:\n{result_str}")

            # Step 3: Parse result
            try:
                logging.info("Start parsing result")
                parsed = ast.literal_eval(result_str)[0]
                logging.info(f"Parsed result:\n{parsed}")
            except Exception as e:
                logging.error(f"Failed to parse SQL result: {e}")
                raise ValueError(f"Result parsing failed: {e}")

            # Step 4: Analyse
            try:
                logging.info("Start analysing metrics")
                metrics_res = self._analyse_metrics(parsed)
            except Exception as e:
                logging.error(f"Failed to analyse metrics: {e}")
                raise ValueError(f"Failed to analyse metrics: {e}")

            elapsed_time = time.time() - start_time
            logging.info(f"Full analysis completed in {elapsed_time:.2f} seconds")
            return metrics_res

        except Exception as e:
            logging.exception("Unexpected error during analysis")
            raise

    def _analyse_metrics(self, parsed_result: list[float]) -> list[dict]:
        metric_order = list(self.metric_weights.keys())

        summary = []
        subtotal = 0.0
        min_metric = None
        min_value = None

        for metric, value in zip(metric_order, parsed_result):
            logging.info(f"Metric: {metric}; Value: {value}")
            weighted = round(value * self.metric_weights[metric], 2)
            summary.append({"label": metric.replace("_", " ").title(), "value": weighted})
            subtotal += weighted
            logging.info(f"weighted: {weighted}; subtotal: {subtotal}")

            if min_value is None or value < min_value:
                min_value = value
                min_metric = metric

        total_score = round(subtotal * 100, 2)
        motivation_zone = (
            "Red" if total_score <= 45 else
            "Yellow" if total_score <= 75 else
            "Green"
        )

        try:
            message_prompt = ChatPromptTemplate.from_template("""
The student's weakest metric is: {metric}.

Write a motivational message (at least 15 tokens) that helps the student improve in this area.
Be optimistic, specific, and helpful. Only return the message text.
""")
            msg_chain = message_prompt | self.llm | StrOutputParser()
            motivation_message = msg_chain.invoke({
                "metric": min_metric.replace("_", " ")
            }).strip()
        except Exception as e:
            logging.error(f"Failed to generate motivational message: {e}")
            motivation_message = "Motivational message could not be generated."

        summary.append({"label": "Subtotal", "value": round(subtotal, 4)})
        summary.append({"label": "Total Score", "value": f"{total_score}%"})
        summary.append({"label": "Motivation Zone", "value": motivation_zone})
        summary.append({"label": "Motivational Message", "value": motivation_message})

        return summary