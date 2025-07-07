from flask import Flask, render_template, request, redirect, url_for, session
from agents.student_sql_agent import StudentSQLAgent
from agents.most_motivated_student_agent import MostMotivatedStudentAgent
from db.postgree_connector import get_postgres_connection
from datetime import datetime
import re
import uuid

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

def get_student_emails():
    try:
        db = get_postgres_connection()
        raw_results = db._execute("SELECT email FROM users ORDER BY email")
        emails = [row["email"] for row in raw_results]
        print("Loaded emails:", emails)
        return emails
    except Exception as e:
        print(f"Error fetching student emails: {e}")
        return []

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

@app.route("/", methods=["GET", "POST"])
def index():
    emails = get_student_emails()

    parsed_input = ""
    parsed_output = ""
    metrics_table = []
    raw_output = ""
    selected_action = ""
    selected_email = ""
    week_from_date = ""
    week_to_date = ""

    if request.method == "POST":
        selected_action = request.form.get("action")
        week_from_date = request.form.get("week_from")
        week_to_date = request.form.get("week_to")
        selected_email = request.form.get("email", "").strip()

        week_from = datetime.strptime(week_from_date, "%Y-%m-%d").isocalendar()[1]
        week_to = datetime.strptime(week_to_date, "%Y-%m-%d").isocalendar()[1]

        if selected_action == "analyse_student" and selected_email:
            agent = StudentSQLAgent(debug=True)
            result = agent.run_analysis(selected_email, week_from, week_to)
        elif selected_action == "most_motivated":
            agent = MostMotivatedStudentAgent(debug=True)
            result = agent.run_analysis(week_from, week_to)
        else:
            result = "Unknown action or missing email."

        if isinstance(result, dict):
            parsed_input = result.get("input", "").replace("\n", "<br>")
            parsed_output = result.get("output", "").replace("\n", "<br>")
            metrics_table = extract_metrics_table(result.get("output", ""))
            raw_output = result
        else:
            parsed_output = result

    return render_template(
        "index.html",
        emails=emails,
        selected_email=selected_email,
        selected_action=selected_action,
        week_from_date=week_from_date,
        week_to_date=week_to_date,
        parsed_input=parsed_input,
        parsed_output=parsed_output,
        raw_output=raw_output,
        metrics_table=metrics_table,
    )