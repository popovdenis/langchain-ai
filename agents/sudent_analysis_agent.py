import ast
import time
import logging
from agents.base import BaseAgent

class StudentAnalysisAgent(BaseAgent):
    def build_sql_prompt(self, email: str, week_from: int, week_to: int) -> str:
        return f"""
        Write an SQL query that:
        1. Finds the ID of the student with email = '{email}'
        2. Selects all student_metrics where week between {week_from} and {week_to} and user_id matches.
        3. Calculates AVG for each of these metrics: homework_submitted, homework_on_time, homework_score, attendance, student_participation, teacher_participation, test_score.
        4. Return values of these metrics only. Exclude id, week.
        Only return a valid SQL query.
        """.strip()

    def run_analysis(self, email: str, week_from: int, week_to: int) -> list[dict]:
        start_time = time.time()
        logging.info("Start analysis")

        try:
            logging.info("Start executing SQL query")
            result = self._build_and_run(self.build_sql_prompt(email, week_from, week_to), stop="\nSQL Result:")

            # Parse result
            logging.info("Start parsing result")
            parsed = ast.literal_eval(result)[0]
            logging.info(f"Parsed result:\n{parsed}")

            # Analyse
            logging.info("Start analysing metrics")
            analysis = self._analyse_metrics(parsed)
        except Exception as e:
            logging.error(f"Error: {e}")
            raise

        elapsed_time = time.time() - start_time
        logging.info(f"Full analysis completed in {elapsed_time:.2f} seconds")

        return analysis