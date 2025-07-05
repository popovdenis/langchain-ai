import argparse
from agents.most_motivated_student_agent import MostMotivatedStudentAgent

def main():
    parser = argparse.ArgumentParser(description="Find the most motivated student in a week range")
    parser.add_argument("--week-from", type=int, required=True)
    parser.add_argument("--week-to", type=int, required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    agent = MostMotivatedStudentAgent(debug=args.debug)
    result = agent.run_analysis(args.week_from, args.week_to)

    print("\n" + "=" * 60)
    print("Most Motivated Student Analysis")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()