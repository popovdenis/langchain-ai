
from config.settings import Settings
import psycopg2
from typing import Dict, Any
import statistics


class StudentMotivationService:
    def __init__(self):
        self.conn = psycopg2.connect(Settings.postgres_dsn())
        self.cursor = self.conn.cursor()

    def calculate_motivation(self, email: str, week_from: int, week_to: int) -> Dict[str, Any]:
        self.cursor.execute("""
            SELECT u.id
            FROM users u
            WHERE u.email = %s
        """, (email,))
        user_row = self.cursor.fetchone()
        if not user_row:
            return {"error": "Student not found"}

        user_id = user_row[0]

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

        # divide columns
        metrics = list(zip(*rows))

        # metrics: 0 и 1 — binary, calculate the arithmetic mean
        avg_homework_submitted = round(statistics.mean(metrics[0]) * 100, 2)
        avg_homework_on_time = round(statistics.mean(metrics[1]) * 100, 2)
        avg_homework_score = round(statistics.mean(metrics[2]), 2)
        avg_attendance = round(statistics.mean(metrics[3]) * 100, 2)
        avg_student_participation = round(statistics.mean(metrics[4]) * 100, 2)
        avg_teacher_participation = round(statistics.mean(metrics[5]) * 100, 2)
        avg_silence = round(statistics.mean(metrics[6]) * 100, 2)
        avg_test_score = round(statistics.mean(metrics[7]), 2)

        # Total motivation score (without weight)
        total_score = round((
            avg_homework_submitted +
            avg_homework_on_time +
            avg_homework_score * 10 +
            avg_attendance +
            avg_student_participation +
            avg_teacher_participation +
            (100 - avg_silence) +  # the less silence, the higher the participation
            avg_test_score * 10
        ) / 8, 2)

        if total_score <= 45:
            zone = "Red"
            message = "Your motivation is very low. Let's talk to your teacher and set small achievable goals."
        elif 45 < total_score <= 75:
            zone = "Yellow"
            message = "You're on your way! A little more consistency and you'll be in the green zone soon."
        else:
            zone = "Green"
            message = "Excellent performance! Keep up the great work!"

        return {
            "student": email,
            "weeks": f"{week_from} to {week_to}",
            "averages": {
                "homework_submitted": avg_homework_submitted,
                "homework_on_time": avg_homework_on_time,
                "homework_score": avg_homework_score,
                "attendance": avg_attendance,
                "student_participation": avg_student_participation,
                "teacher_participation": avg_teacher_participation,
                "silence": avg_silence,
                "test_score": avg_test_score,
            },
            "total_score": total_score,
            "zone": zone,
            "message": message,
        }

    def __del__(self):
        self.cursor.close()
        self.conn.close()