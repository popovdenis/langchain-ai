from agents.student_sql_agent import StudentSQLAgent

if __name__ == "__main__":
    agent = StudentSQLAgent(model_name="gpt-3.5-turbo")  # replace to gpt-4 later
    prompt = "Find students who missed homework in the last weeks and have test scores below 5."
    result = agent.run_query(prompt)
    print(result)