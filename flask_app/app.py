from flask import Flask, render_template, request, jsonify
from agents.student_sql_agent import StudentSQLAgent
from agents.most_motivated_student_agent import MostMotivatedStudentAgent
from datetime import datetime
import math
import re
import psycopg2
from config.settings import Settings

app = Flask(__name__)

def get_paginated_students(page: int, per_page: int = 10):
    offset = (page - 1) * per_page
    try:
        conn = psycopg2.connect(Settings.postgres_dsn())
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT email FROM users ORDER BY email LIMIT %s OFFSET %s", (per_page, offset))
        rows = cursor.fetchall()

        students = [{"email": row[0]} for row in rows]

        cursor.close()
        conn.close()
        return students, total
    except Exception as e:
        print(f"Error fetching students: {e}")
        return [], 0

def extract_metrics_table(output: str) -> list[dict]:
    metrics = []
    table_match = re.search(r"\| *Metric.*?\|.*?\|([\s\S]+?)\n\n", output)
    if not table_match:
        return metrics

    lines = table_match.group(1).strip().splitlines()
    for line in lines:
        parts = [col.strip() for col in line.strip("|").split("|")]
        if len(parts) == 2:
            metrics.append({"metric": parts[0], "average": parts[1]})
    return metrics

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/students", methods=["GET"])
def students_table():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    students, total = get_paginated_students(page)
    total_pages = math.ceil(total / 10)
    return render_template("partials/table.html", students=students, page=page, total_pages=total_pages)

@app.route("/analysis", methods=["POST"])
def student_analysis():
    try:
        data = request.get_json()
        action = data.get("action")
        week_from_str = data.get("week_from")
        week_to_str = data.get("week_to")
        email = data.get("email")
        num_students = int(data.get("num_students", 1))

        week_from = datetime.strptime(week_from_str, "%Y-%m-%d").isocalendar().week
        week_to = datetime.strptime(week_to_str, "%Y-%m-%d").isocalendar().week

        if action == "analyse_student":
            agent = StudentSQLAgent(debug=False)
            result = agent.run_analysis(email, week_from, week_to)
        elif action == "most_motivated":
            agent = MostMotivatedStudentAgent(debug=True)
            result = agent.run_analysis(week_from, week_to)
        else:
            return jsonify({"error": "Unknown action"}), 400

        print("Result: ", result)

        parsed_input = result.get("input", "").replace("\n", "<br>") if isinstance(result, dict) else ""
        parsed_output = result.get("output", "").replace("\n", "<br>") if isinstance(result, dict) else result
        metrics_table = extract_metrics_table(parsed_output)

        html = render_template(
            "partials/analysis.html",
            parsed_input=parsed_input,
            parsed_output=parsed_output,
            metrics_table=metrics_table,
            student_email=email
        )
        return jsonify({"html": html})

    except Exception as e:
        return jsonify({"error": str(e)}), 500