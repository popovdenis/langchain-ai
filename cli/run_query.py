import argparse
from agents.student_sql_agent import StudentSQLAgent

def main():
    parser = argparse.ArgumentParser(description="Run LangChain SQL agent by request")
    parser.add_argument("--query", type=str, required=True, help="Find students without home work")
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo", help="Model OpenAI")
    parser.add_argument("--week", type=int, default=None, help="Current week (for instance, 27")
    args = parser.parse_args()

    agent = StudentSQLAgent(model_name=args.model)
    result = agent.run_query(args.query)
    print("\nAgent answer:\n")
    print(result)

if __name__ == "__main__":
    main()