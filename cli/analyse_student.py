import argparse
from agents.student_sql_agent import StudentSQLAgent

def main():
    parser = argparse.ArgumentParser(description="Analyse student performance based on email and week range")
    parser.add_argument("--email", required=True, help="Student email address")
    parser.add_argument("--week-from", type=int, required=True, help="Start of the week range")
    parser.add_argument("--week-to", type=int, required=True, help="End of the week range")
    parser.add_argument("--debug", type=bool, help="Enable verbose debug output")
    args = parser.parse_args()

    agent = StudentSQLAgent(debug=args.debug)
    result = agent.run_analysis(args.email, args.week_from, args.week_to)

    print("\n" + "=" * 60)
    print(result)
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()