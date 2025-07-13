from flask import Flask, render_template, request, jsonify
from agents.student_sql_agent import StudentSQLAgent
from agents.most_motivated_student_agent import MostMotivatedStudentAgent
# from agents.student_motivation_agent import StudentMotivationAgent
import math
import re
import mysql.connector
from config.settings import Settings

app = Flask(__name__)
application = app

def get_paginated_students(page: int, per_page: int = 10):
    offset = (page - 1) * per_page
    try:
        conn = mysql.connector.connect(**Settings.mysql_dsn())
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
        week_from = data.get("week_from")
        week_to = data.get("week_to")
        email = data.get("email")
        num_students = int(data.get("num_students", 1))

        if action == "analyse_student":
            agent = StudentSQLAgent()
            result = agent.run_analysis(email, week_from, week_to)
        elif action == "most_motivated":
            agent = MostMotivatedStudentAgent()
            result = agent.run_analysis(week_from, week_to)
        else:
            return jsonify({"error": "Unknown action"}), 400

        html = render_template(
            "partials/analysis.html",
            metrics_table=result,
            student_email=email
        )
        return jsonify({"html": html})

    except Exception as e:
        return jsonify({"error": str(e)}), 500