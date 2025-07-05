import random
import psycopg2
from faker import Faker
from config.settings import Settings

fake = Faker()

def generate_fake_data(num_students=100, weeks=52):
    conn = psycopg2.connect(Settings.postgres_dsn())
    cursor = conn.cursor()

    # Clear tables
    cursor.execute("DELETE FROM student_metrics;")
    cursor.execute("DELETE FROM users;")
    conn.commit()

    for _ in range(num_students):
        email = fake.email()
        cursor.execute("INSERT INTO users (email) VALUES (%s) RETURNING id;", (email,))
        user_id = cursor.fetchone()[0]

        for week in range(1, weeks + 1):
            attendance = round(random.uniform(0.5, 1.0), 2)
            homework_submitted = random.choice([True, False])
            homework_on_time = homework_submitted and random.choice([True, False])
            homework_score = round(random.uniform(4.0, 9.0), 1) if homework_submitted else 0.0
            test_score = round(random.uniform(4.0, 9.0), 1)
            student_talk = round(random.uniform(0.1, 0.6), 2)
            teacher_talk = round(random.uniform(0.3, 0.8), 2)
            silence = round(1.0 - (student_talk + teacher_talk), 2)

            cursor.execute("""
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

    conn.commit()
    cursor.close()
    conn.close()
    print("Fake data inserted.")

if __name__ == "__main__":
    generate_fake_data()