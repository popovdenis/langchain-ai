from flask import Flask, render_template, request, jsonify
from agents.motivated_student_agent import MotivatedStudentAgent
from agents.sudent_motivation_agent2 import StudentMotivationAgent2
import math
import re
import mysql.connector
from config.settings import Settings
from datetime import datetime

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
    current_week = datetime.now().isocalendar()[1]
    return render_template("index.html", current_week=current_week)

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
            agent = StudentMotivationAgent2()
            result = agent.run_analysis(email, week_from, week_to)
            html = render_template(
                "partials/analysis.html",
                metrics_table=result,
                student_email=email
            )
        elif action == "most_motivated":
            agent = MotivatedStudentAgent()
            result = agent.run_analysis('highest', week_from, week_to, num_students)

            html = render_template(
                "partials/motivated.html",
                metrics_table=result
            )
        elif action == "less_motivated":
            agent = MotivatedStudentAgent()
            result = agent.run_analysis('lowest', week_from, week_to, num_students)

            html = render_template(
                "partials/motivated.html",
                metrics_table=result
            )
        else:
            return jsonify({"error": "Unknown action"}), 400

        return jsonify({"html": html})

    except Exception as e:
        return jsonify({"error": str(e)}), 500