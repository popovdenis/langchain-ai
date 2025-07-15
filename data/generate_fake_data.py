import random
import mysql.connector
import os
import logging
from datetime import datetime
from faker import Faker
from config.settings import Settings

fake = Faker()

class MetricsGenerator:
    def __init__(self):
        self.mydb = mysql.connector.connect(
            host=Settings.MYSQL_HOST,
            user=Settings.MYSQL_USER,
            password=Settings.MYSQL_PASSWORD,
            database=Settings.MYSQL_DB
        )
        self.conn = mysql.connector.connect(**Settings.mysql_dsn())
        self.cursor = self.conn.cursor()
        self.levels = ["red", "yellow", "green"]

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

    def generate_and_insert_metrics(self, user_id, weeks=10, motivation_level="random"):
        for week in range(1, weeks + 1):
            if motivation_level == "green":
                base_min, base_max = 0.76, 1.0
            elif motivation_level == "yellow":
                base_min, base_max = 0.4, 0.7
            elif motivation_level == "red":
                base_min, base_max = 0.1, 0.4
            else:
                base_min, base_max = 0.1, 1.0

            attendance = round(random.uniform(base_min, base_max), 2)
            homework_submitted = round(random.uniform(base_min, base_max), 2)
            homework_on_time = round(random.uniform(base_min, base_max), 2)
            homework_score = round(random.uniform(base_min, base_max), 2)
            test_score = round(random.uniform(base_min, base_max), 2)
            student_talk = round(random.uniform(base_min, base_max), 2)
            teacher_talk = round(random.uniform(base_min, base_max), 2)
            silence = round(random.uniform(
                max(0.03, 1.0 - base_max),
                min(0.3, 1.0 - base_min)
            ), 2)

            self.cursor.execute("""
                INSERT INTO student_metrics (
                    user_id, week, attendance,
                    homework_submitted, homework_on_time, homework_score,
                    test_score, student_participation, teacher_participation, silence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, week, attendance,
                homework_submitted, homework_on_time, homework_score,
                test_score, student_talk, teacher_talk, silence
            ))

    def clear_metrics(self):
        logging.info("Clearing metrics table")
        self.cursor.execute("DELETE FROM student_metrics;")
        self.cursor.execute("DELETE FROM users;")
        self.conn.commit()

    def generate_metrics(self, num_students=100, weeks=52):
        logging.info("Starting generation of metrics")
        for _ in range(num_students):
            email = fake.email()
            logging.info(f"New user email: {email}")

            try:
                self.cursor.execute("INSERT INTO users (email) VALUES (%s) RETURNING id;", (email,))
                user_id = self.cursor.fetchone()[0]
                logging.info(f"User ID: {user_id}")
            except Exception as e:
                logging.error(f"Error while inserting a new user: {e}")
                raise

            level = random.choice(self.levels)
            try:
                self.generate_and_insert_metrics(user_id, weeks=weeks, motivation_level=level)
                logging.info(f"User ID: {user_id}; Weeks: 1-{weeks}; Level: {level}")
            except Exception as e:
                logging.error(f"Error while inserting metrics: {e}")
                raise

        self.conn.commit()
        self.cursor.close()
        self.conn.close()
        print("Fake data inserted.")

if __name__ == "__main__":
    generator = MetricsGenerator()
    generator.clear_metrics()
    generator.generate_metrics()