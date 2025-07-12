import os
import psycopg2
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

class StudentMotivationAgent:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_API_MODEL", "gpt-4")  # укажи нужную модель в .env

        if not self.db_url or not self.openai_api_key:
            raise ValueError("DATABASE_URL or OPENAI_API_KEY missing in .env")

        self.llm = ChatOpenAI(api_key=self.openai_api_key, model=self.openai_model)
        self.sql_prompt = PromptTemplate.from_template("""
You are a PostgreSQL assistant.

Given:
- student email: {email}
- week range: {week_from} to {week_to}

Generate ONE valid SQL query in PostgreSQL that selects:
- week
- homework_submitted
- homework_on_time
- homework_score
- attendance
- student_participation
- test_score

Only return the SQL. Do not say anything else.
SQL:
""")

        self.message_prompt = PromptTemplate.from_template("""
You are a motivational educational assistant.

Given:
- a dictionary of average performance metrics: {metrics}
- the weakest metric: {weakest_metric}

Generate an encouraging motivational message in English that helps the student improve their {weakest_metric}.
The message should be practical, optimistic, and mention the weak metric clearly.

Motivational Message:
""")
        self.sql_chain = (
            {"email": lambda x: x["email"], "week_from": lambda x: x["week_from"], "week_to": lambda x: x["week_to"]}
            | self.sql_prompt
            | self.llm
            | StrOutputParser()
        )

        self.message_chain = (
            {"metrics": lambda x: x["metrics"], "weakest_metric": lambda x: x["weakest_metric"]}
            | self.message_prompt
            | self.llm
            | StrOutputParser()
        )

    def run_analysis(self, email: str, week_from: int, week_to: int) -> list[dict]:
        try:
            print("params:", email, week_from, week_to)
            sql_query = self.sql_chain.invoke({
                "email": email,
                "week_from": week_from,
                "week_to": week_to
            }).strip()
        except Exception as e:
            print("error:", e)
            return [{"label": "LLM Error", "value": f"Failed to parse SQL: {e}"}]

        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            print("error:", e)
            return [{"label": "Error", "value": f"Query execution error: {e}"}]

        # handle results
        if not rows:
            return [{"label": "Info", "value": "No data found for this student and range"}]

        metric_names = ["homework_submitted", "homework_on_time", "homework_score",
                        "attendance", "student_participation", "test_score"]

        # aggregate
        metric_sums = {k: 0.0 for k in metric_names}
        for row in rows:
            for i, key in enumerate(metric_names, start=1):
                metric_sums[key] += float(row[i])

        total_weeks = len(rows)
        metric_averages = {k: round(v / total_weeks, 4) for k, v in metric_sums.items()}

        # collect metrics
        metric_weights = {
            "homework_submitted": float(os.getenv("WEIGHT_HOMEWORK_SUBMITTED", 1.0)),
            "homework_on_time": float(os.getenv("WEIGHT_HOMEWORK_ON_TIME", 1.0)),
            "homework_score": float(os.getenv("WEIGHT_HOMEWORK_SCORE", 1.0)),
            "attendance": float(os.getenv("WEIGHT_ATTENDANCE", 1.0)),
            "student_participation": float(os.getenv("WEIGHT_STUDENT_PARTICIPATION", 1.0)),
            "test_score": float(os.getenv("WEIGHT_TEST_SCORE", 1.0)),
        }

        subtotal = sum(metric_averages[k] * metric_weights[k] for k in metric_names)
        total_score = round(subtotal * 100, 2)
        weakest_metric = min(metric_averages, key=metric_averages.get)

        # motivation message
        try:
            message = self.message_chain.invoke({
                "metrics": str(metric_averages),
                "weakest_metric": weakest_metric.replace("_", " ").title()
            }).strip()
        except Exception as e:
            return [{"label": "LLM Error", "value": f"Failed to parse: {e}"}]

        zone = "Red" if total_score <= 45 else "Yellow" if total_score <= 75 else "Green"

        result_data = []

        for k, v in metric_averages.items():
            label = k.replace("_", " ").title()
            result_data.append({"label": label, "value": round(v, 4)})

        result_data.append({"label": "Subtotal", "value": round(subtotal, 4)})
        result_data.append({"label": "Total Score", "value": f"{total_score}%"})
        result_data.append({"label": "Motivation Zone", "value": zone})
        result_data.append({"label": "Motivational Message", "value": message})

        return result_data