import os
import psycopg2
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from config.settings import Settings

load_dotenv()

openai_api_key = Settings.OPENAI_API_KEY
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env")

# Веса метрик из .env
METRIC_WEIGHTS = {
    "homework_submitted": float(os.getenv("WEIGHT_HOMEWORK_SUBMITTED", 0.1)),
    "homework_on_time": float(os.getenv("WEIGHT_HOMEWORK_ON_TIME", 0.1)),
    "homework_score": float(os.getenv("WEIGHT_HOMEWORK_SCORE", 0.2)),
    "attendance": float(os.getenv("WEIGHT_ATTENDANCE", 0.2)),
    "student_participation": float(os.getenv("WEIGHT_STUDENT_PARTICIPATION", 0.2)),
    "test_score": float(os.getenv("WEIGHT_TEST_SCORE", 0.2)),
}

METRIC_FIELDS = list(METRIC_WEIGHTS.keys())

prompt_template = PromptTemplate.from_template("""
You are a motivational AI coach.

Given the student's performance metrics (averaged over multiple weeks), and the weakest metric identified,
generate a short motivational message (2–4 sentences). The message **must explicitly mention the weakest metric by name** and offer advice for improvement.

Metrics:
{metrics}

Weakest metric:
{weakest_metric}
""")

llm = ChatOpenAI(
            temperature=0,
            model=Settings.OPENAI_API_MODEL,
            api_key=Settings.OPENAI_API_KEY,
            streaming=False
        )

chain = (
    {"metrics": RunnablePassthrough(), "weakest_metric": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)

def analyze_student(email: str, week_from: int, week_to: int) -> list[dict]:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Получение user_id
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"No user found with email: {email}")
    user_id = row[0]

    # Получение данных метрик
    sql = f"""
        SELECT {", ".join(METRIC_FIELDS)}
        FROM student_metrics
        WHERE user_id = %s AND week BETWEEN %s AND %s
    """
    cur.execute(sql, (user_id, week_from, week_to))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise ValueError("No metrics found for the given week range.")

    # Расчёт средних значений
    metric_sums = {key: 0.0 for key in METRIC_FIELDS}
    for row in rows:
        for idx, key in enumerate(METRIC_FIELDS):
            metric_sums[key] += row[idx]

    total_records = len(rows)
    metric_averages = {key: metric_sums[key] / total_records for key in METRIC_FIELDS}

    # Расчёт subtotal и total
    subtotal = sum(metric_averages[k] * METRIC_WEIGHTS[k] for k in METRIC_FIELDS)
    total_score = round(subtotal * 100, 2)

    # Определение слабой метрики
    weakest_metric = min(metric_averages.items(), key=lambda x: x[1])[0]

    # Получение мотивационного сообщения
    motivational_message = chain.invoke({
        "metrics": str(metric_averages),
        "weakest_metric": weakest_metric.replace("_", " ").title()
    }).strip()

    # Определение зоны
    if total_score <= 45:
        zone = "Red"
    elif total_score <= 75:
        zone = "Yellow"
    else:
        zone = "Green"

    # Финальный ответ
    result_data = []
    for metric, value in metric_averages.items():
        result_data.append({"label": metric.replace("_", " ").title(), "value": round(value, 4)})
    result_data.append({"label": "Subtotal", "value": round(subtotal, 4)})
    result_data.append({"label": "Total Score", "value": f"{total_score}%"})
    result_data.append({"label": "Motivation Zone", "value": zone})
    result_data.append({"label": "Motivational Message", "value": motivational_message})

    return result_data