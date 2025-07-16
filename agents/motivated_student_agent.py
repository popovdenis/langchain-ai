import ast
import time

from agents.base import BaseAgent

class MotivatedStudentAgent(BaseAgent):
    def _get_user_ids(self, metric_type: str, week_from: int, week_to: int, num_students: int = 1):
        # Build SQL query using LLM for top motivated students
        self.logger.info("Build SQL query using LLM for top motivated students")
        question = self._build_metrics_prompt(metric_type, week_from, week_to, num_students)
        sql = self._run_llm_sql_chain(question)

        self.logger.info(f"SQL for building metrics: {sql}")
        self.mycursor.execute(sql)
        rows = self.mycursor.fetchall()
        self.logger.info(f"SQL #1 result: {rows}")

        if not rows:
            self.logger.warning("No rows returned from SQL #1")
            return []

        return rows

    def _get_users_by_ids(self, user_ids):
        email_query = self._build_user_prompt_bulk(user_ids)
        sql = self._run_llm_sql_chain(email_query, stop="\nSQL Result:")
        result = self.db.run(sql)

        return {row[0]: row[1] for row in ast.literal_eval(result)}

    def run_analysis(self, metric_type: str, week_from: int, week_to: int, num_students: int):
        start_time = time.time()
        self.logger.info("Start: most motivated student analysis")

        try:
            # Get user emails in bulk
            users = self._get_user_ids(metric_type, week_from, week_to, num_students)
            id_to_email = self._get_users_by_ids([row[0] for row in users])
        except Exception as e:
            self.logger.error(f"Failed to parse email list: {e}")
            raise ValueError("Could not extract emails from result")

        # Analyse each user individually
        summary = []
        for user in users:
            try:
                user_id = user[0]
                metric_values = user[1:]
                email = id_to_email.get(user_id, f"user-{user_id}@unknown.local")
            except Exception as e:
                self.logger.error(f"Parse error in row: {e}")
                continue

            try:
                self.logger.info(f"Start analysing metrics for user_id={user_id}")
                metrics_res = self._analyse_metrics(metric_values)
            except Exception as e:
                self.logger.error(f"Failed to analyse metrics for user_id={user_id}: {e}")
                continue

            summary.append({"email": email, "metrics": metrics_res})

        elapsed_time = time.time() - start_time
        self.logger.info(f"Full analysis completed in {elapsed_time:.2f} seconds")

        return summary

    def _build_metrics_prompt(self, metric_type: str, week_from: int, week_to: int, num_students: int = 1) -> str:
        return f"""
        From the `student_metrics` table:
        1. For each user_id, calculate average of all metrics (excluding id, user_id, week).
        2. Identify top {num_students} users with the {metric_type} overall average across all these metrics.
        3. Return:
           - user_id
           - avg_homework_submitted
           - avg_homework_on_time
           - avg_homework_score
           - avg_attendance
           - avg_student_participation
           - avg_teacher_participation
           - avg_test_score
        Only return SQL. Use: WHERE week BETWEEN {week_from} AND {week_to}.
        """.strip()

    def _build_user_prompt_bulk(self, user_ids: list[int]) -> str:
        ids_str = ", ".join(map(str, user_ids))

        return f"""
        From the `users` table, return id and email for users with id in ({ids_str}).
        Return two columns: id, email.
        """.strip()