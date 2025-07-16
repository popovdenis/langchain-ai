from config.settings import Settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
import os
import argparse
import time
import ast

os.environ['OPENAI_API_KEY'] = Settings.OPENAI_API_KEY
os.environ['OPENAI_API_MODEL'] = Settings.OPENAI_API_MODEL

prompt = ChatPromptTemplate.from_template("""
Based on the table schema below, write an SQL query that would answer the user's question:
{schema}

Question: {question}
SQL Query:
""")
prompt2 = ChatPromptTemplate.from_template("""
Based on the table schema below, a the text message (at least 15 tokens) that would answer the user's question:
{schema}

Question: {question}
SQL Query:
""")

db_uri = "mysql+mysqlconnector://root:root@localhost:3306/langchain_ai"
db = SQLDatabase.from_uri(db_uri)

def get_schema(_):
    return db.get_table_info()

llm = ChatOpenAI()

sql_chain = (
    RunnablePassthrough.assign(schema=get_schema)
    | prompt
    | llm.bind(stop="\SQL Result:")
    | StrOutputParser()
)
sql_chain2 = (
    RunnablePassthrough.assign(schema=get_schema)
    | prompt2
    | llm
    | StrOutputParser()
)

analysis_prompt = ChatPromptTemplate.from_template("""
Based on the table schema below, question, sql query and sql response, write a natural language response:
{schema}

Question: {question}
SQL Query: {query}
SQL Response: {response}
""")

def run_query(query):
    return db.run(query)

def build_prompt(email: str, week_from: int, week_to: int) -> str:
    return f"""
You are an expert in writing SQL queries.

Given the following conditions:
- There is a 'users' table with columns: id, email
- There is a 'student_metrics' table with columns:
  homework_submitted, homework_on_time, homework_score, attendance, student_participation, teacher_participation, silence, test_score

Write an SQL query that:
1. Finds the ID of the student with email = '{email}'
2. Selects all student_metrics for this student where week is between {week_from} and {week_to}
3. Calculates the average of each metric (except id, user_id, week)
4. Returns list of metrics per average value

Only return a valid SQL query.
"""

def analyse_metrics(result_str: str) -> dict:
    weights = {
        "homework_submitted": float(os.getenv("WEIGHT_HOMEWORK_SUBMITTED", 0.1)),
        "homework_on_time": float(os.getenv("WEIGHT_HOMEWORK_ON_TIME", 0.1)),
        "homework_score": float(os.getenv("WEIGHT_HOMEWORK_SCORE", 0.2)),
        "attendance": float(os.getenv("WEIGHT_ATTENDANCE", 0.2)),
        "student_participation": float(os.getenv("WEIGHT_STUDENT_PARTICIPATION", 0.1)),
        "teacher_participation": float(os.getenv("WEIGHT_TEACHER_PARTICIPATION", 0.1)),
        "silence": float(os.getenv("WEIGHT_SILENCE", 0.1)),
        "test_score": float(os.getenv("WEIGHT_TEST_SCORE", 0.1)),
    }

    metric_order = list(weights.keys())

    try:
        parsed_result = ast.literal_eval(result_str)[0]
    except Exception as e:
        raise ValueError(f"Failed to parse result string: {e}")

    if len(parsed_result) != len(metric_order):
        raise ValueError("Parsed metrics count doesn't match expected metrics")

    summary = []
    subtotal = 0.0
    min_metric = None
    min_value = None

    for metric, value in zip(metric_order, parsed_result):
        summary.append({
            "metric": metric,
            "average": round(value * 100, 2)
        })
        weighted = value * weights[metric]
        subtotal += weighted

        if min_value is None or value < min_value:
            min_value = value
            min_metric = metric

    total_score = round(subtotal * 100, 2)

    if total_score <= 45:
        zone = "Red"
    elif 45 < total_score <= 75:
        zone = "Yellow"
    else:
        zone = "Green"

    prompt = f"""
The student's weakest metric is: {min_metric.replace('_', ' ')}.

Write a motivational message (at least 15 tokens) that encourages the student to improve in this area.
Be optimistic, specific, and helpful. Only return the message text.
""".strip()
    generated_message = sql_chain2.invoke({"question": prompt})

    return {
        "summary": summary,
        "subtotal": round(subtotal, 4),
        "total_score": total_score,
        "motivation_zone": zone,
        "motivation_message_prompt": generated_message
    }

full_chain = (
    RunnablePassthrough.assign(query=sql_chain)
    .assign(
        schema=get_schema,
        response=lambda vars: run_query(vars["query"]),
    )
    | analysis_prompt
    | llm
    | StrOutputParser()
)

if __name__ == "__main__":
    start_time = time.time()

    parser = argparse.ArgumentParser(description="Analyse student performance based on email and week range")
    parser.add_argument("--email", required=True, help="Student email address")
    parser.add_argument("--week-from", type=int, required=True, help="Start of the week range")
    parser.add_argument("--week-to", type=int, required=True, help="End of the week range")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug output")
    args = parser.parse_args()

    try:
        # Step 1: SQL Generation Chain (question → sql)
        question = build_prompt(args.email, args.week_from, args.week_to)
        print("Question:\n", question)

        print("\nGenerating SQL...")
        generated_sql = sql_chain.invoke({"question": question})
        print("Generated SQL:\n", generated_sql)

        # Step 2: Execute SQL → get result
        print("\nExecute SQL → get result...")
        result_dict = db.run(generated_sql)
        print("Result:\n", result_dict)

        # Step 3: Metrics analysis → Python или Prompt
        print("\nExecute SQL → get result...")
        summary = analyse_metrics(result_dict)
        print("Result:\n", summary)

        # Step 4: Generate final message (prompt → json)
        # final_response = final_chain.invoke({
        #     "metrics": summary["metrics"],
        #     "subtotal": summary["subtotal"],
        #     "total_score": summary["total_score"],
        #     "weakest_metric": summary["weakest_metric"],
        # })


        # sql = sql_chain.invoke({"question": question})
        # print("Generated SQL:\n", sql)

        # result = full_chain.invoke({"question": question})
        # print("\nFinal Result:\n", result)

        elapsed_time = time.time() - start_time
        print(f"\nFull time: {elapsed_time:.2f} seconds")
    except Exception as e:
        print("Error while invoking agent:", e)
        raise
