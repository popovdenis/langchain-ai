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

class MostMotivatedStudentAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Settings.OPENAI_API_KEY,
            model=Settings.OPENAI_API_MODEL
        )
        self.db = SQLDatabase.from_uri(Settings.mysql_uri())
        self.metric_weights = {
            "homework_submitted": float(os.getenv("WEIGHT_HOMEWORK_SUBMITTED", 0.1)),
            "homework_on_time": float(os.getenv("WEIGHT_HOMEWORK_ON_TIME", 0.1)),
            "homework_score": float(os.getenv("WEIGHT_HOMEWORK_SCORE", 0.2)),
            "attendance": float(os.getenv("WEIGHT_ATTENDANCE", 0.2)),
            "student_participation": float(os.getenv("WEIGHT_STUDENT_PARTICIPATION", 0.1)),
            "teacher_participation": float(os.getenv("WEIGHT_TEACHER_PARTICIPATION", 0.1)),
            "test_score": float(os.getenv("WEIGHT_TEST_SCORE", 0.1)),
        }
        self._configure_logger()

    def _configure_logger(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"logging_{today}.log")
        logging.basicConfig(
            filename=log_file,
            filemode='a',
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        logging.getLogger().addHandler(logging.StreamHandler())

    def get_schema(self, _=None):
        return self.db.get_table_info()

    def build_metrics_prompt(self, week_from: int, week_to: int) -> str:
        return f"""
    From the `student_metrics` table:
    1. For each user_id, calculate average of all metrics (excluding id, user_id, week).
    2. Identify the student with the highest overall average across all these metrics (i.e. sum of all averages divided by number of metrics).
    3. Return:
       - user_id
       - all avg metrics in this order:
         homework_submitted, homework_on_time, homework_score, attendance,
         student_participation, teacher_participation, test_score
    One row only. SQL only.
    WHERE week BETWEEN {week_from} AND {week_to}
    """.strip()

    def build_user_prompt(self, user_id: int) -> str:
        return f"""
From the `users` table, return email for user with id = {user_id}.
Return a single column: email.
""".strip()

    def run_analysis(self, week_from: int, week_to: int):
        start_time = time.time()
        logging.info("Start: most motivated student analysis")

        # 1. Step: find user_id with best average metrics
        prompt = ChatPromptTemplate.from_template("""
            Use schema to answer question. Return valid SQL only.
            Schema:
            {schema}
            
            Question:
            {question}
            SQL Query:
        """)
        sql_chain = (
            RunnablePassthrough.assign(schema=self.get_schema)
            | prompt
            | self.llm.bind(stop="\nSQL Result:")
            | StrOutputParser()
        )
        question = self.build_metrics_prompt(week_from, week_to)

        sql = sql_chain.invoke({"question": question})
        logging.info(f"SQL #1:\n{sql}")

        sql = sql.strip()
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").strip()
        if sql.endswith("```"):
            sql = sql[:-3].strip()

        result = self.db.run(sql)
        logging.info(f"SQL #1 result: {result}")

        # 2. Parse the result
        try:
            parsed = ast.literal_eval(result)[0]
            user_id = parsed[0:]
            metric_values = parsed[1:]
        except Exception as e:
            logging.error(f"Parse error in result: {e}")
            raise ValueError("Invalid result from SQL #1")

        # 2. Step: get email by user_id
        question2 = self.build_user_prompt(user_id)
        sql_chain2 = (
                RunnablePassthrough.assign(schema=self.get_schema)
                | prompt
                | self.llm.bind(stop="\nSQL Result:")
                | StrOutputParser()
        )
        sql2 = sql_chain2.invoke({"question": question2})
        logging.info(f"SQL #2:\n{sql2}")

        sql2 = sql2.strip()
        if sql2.startswith("```sql"):
            sql2 = sql2.replace("```sql", "").strip()
        if sql2.endswith("```"):
            sql2 = sql2[:-3].strip()

        result2 = self.db.run(sql2)
        logging.info(f"SQL #2 result: {result2}")
        try:
            email = ast.literal_eval(result2)[0][0]
        except Exception as e:
            logging.error(f"Parse error in result2: {e}")
            raise ValueError("Could not extract email")

        # Step 2: Analyse
        try:
            logging.info("Start analysing metrics")
            metrics_res = self._analyse_metrics(metric_values)
        except Exception as e:
            logging.error(f"Failed to analyse metrics: {e}")
            raise ValueError(f"Failed to analyse metrics: {e}")

        elapsed_time = time.time() - start_time
        logging.info(f"Full analysis completed in {elapsed_time:.2f} seconds")

        return {
            "email": email,
            "metrics": metrics_res,
        }

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
                Write a motivational message (15+ tokens) to help improve. Return only the message.
            """)
            message_chain = message_prompt | self.llm | StrOutputParser()
            motivation_message = message_chain.invoke({"metric": min_metric.replace("_", " ")}).strip()
        except Exception as e:
            logging.error(f"Failed to generate motivational message: {e}")
            motivation_message = "Motivational message could not be generated."

        summary.append({"label": "Subtotal", "value": round(subtotal, 4)})
        summary.append({"label": "Total Score", "value": f"{total_score}%"})
        summary.append({"label": "Motivation Zone", "value": motivation_zone})
        summary.append({"label": "Motivational Message", "value": motivation_message})

        return summary