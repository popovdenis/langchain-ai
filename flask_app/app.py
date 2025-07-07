from flask import Flask, render_template, request, jsonify
from agents.student_sql_agent import StudentSQLAgent
from agents.most_motivated_student_agent import MostMotivatedStudentAgent
from db.postgree_connector import get_postgres_connection

app = Flask(__name__)

@app.route("/api/students")
def api_students():
    emails = get_student_emails()
    return jsonify(emails)

def get_student_emails():
    try:
        db = get_postgres_connection()
        raw_results = db._execute("SELECT email FROM users ORDER BY email")
        emails = [row['email'] for row in raw_results]
        return emails
    except Exception as e:
        print(f"Error fetching student emails: {e}")
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    emails = get_student_emails()
    output = ""

    if request.method == "POST":
        action = request.form.get("action")
        week_from = int(request.form.get("week_from", 0))
        week_to = int(request.form.get("week_to", 0))
        email = request.form.get("email", "").strip()

        if action == "analyse_student" and email:
            agent = StudentSQLAgent(debug=True)
            output = agent.run_analysis(email, week_from, week_to)
        elif action == "most_motivated":
            agent = MostMotivatedStudentAgent(debug=True)
            output = agent.run_analysis(week_from, week_to)
        else:
            output = "Unknown action or missing email."

    return render_template("index.html", emails=emails, output=output)


