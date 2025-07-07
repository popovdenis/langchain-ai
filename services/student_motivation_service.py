from decimal import Decimal
from typing import Dict, Any
import psycopg2
import statistics
from config.settings import Settings


class StudentMotivationService:
    def __init__(self):
        self.conn = psycopg2.connect(Settings.postgres_dsn())
        self.cursor = self.conn.cursor()
        self.weights = {
            "homework_submitted": Decimal(Settings.WEIGHT_HOMEWORK_SUBMITTED),
            "homework_on_time": Decimal(Settings.WEIGHT_HOMEWORK_ON_TIME),
            "homework_score": Decimal(Settings.WEIGHT_HOMEWORK_SCORE),
            "attendance": Decimal(Settings.WEIGHT_ATTENDANCE),
            "student_participation": Decimal(Settings.WEIGHT_STUDENT_PARTICIPATION),
            "teacher_participation": Decimal(Settings.WEIGHT_TEACHER_PARTICIPATION),
            "silence": Decimal(Settings.WEIGHT_SILENCE),
            "test_score": Decimal(Settings.WEIGHT_TEST_SCORE),
        }

    def calculate_motivation(self, email: str, week_from: int, week_to: int) -> Dict[str, Any]:
        self.cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = self.cursor.fetchone()
        if not row:
            return {"error": "Student not found"}
        user_id = row[0]

        self.cursor.execute("""
            SELECT
                homework_submitted,
                homework_on_time,
                homework_score,
                attendance,
                student_participation,
                teacher_participation,
                silence,
                test_score
            FROM student_metrics
            WHERE user_id = %s AND week BETWEEN %s AND %s
        """, (user_id, week_from, week_to))

        rows = self.cursor.fetchall()
        if not rows:
            return {"error": "No data for given weeks"}

        metrics = list(zip(*rows))

        averages = {
            "homework_submitted": round(statistics.mean(metrics[0]), 4),
            "homework_on_time": round(statistics.mean(metrics[1]), 4),
            "homework_score": round(statistics.mean(metrics[2]), 4),
            "attendance": round(statistics.mean(metrics[3]), 4),
            "student_participation": round(statistics.mean(metrics[4]), 4),
            "teacher_participation": round(statistics.mean(metrics[5]), 4),
            "silence": round(statistics.mean(metrics[6]), 4),
            "test_score": round(statistics.mean(metrics[7]), 4),
        }

        # Calculate subtotal и total
        subtotal = sum(averages[key] * self.weights[key] for key in averages)
        total = round(subtotal * 100, 2)

        # Find the lowest
        lowest_metric = min(
            {k: v for k, v in averages.items() if k != "silence"}, key=averages.get
        )

        return {
            "student": email,
            "weeks": f"{week_from} to {week_to}",
            "averages": averages,
            "subtotal": float(round(subtotal, 4)),
            "total": float(total),
            "lowest_metric": lowest_metric
        }

    def __del__(self):
        self.cursor.close()
        self.conn.close()