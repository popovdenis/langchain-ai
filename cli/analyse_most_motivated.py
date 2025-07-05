import argparse
from agents.most_motivated_student_agent import MostMotivatedStudentAgent

def main():
    parser = argparse.ArgumentParser(description="Find the most motivated student.")
    parser.add_argument("--week-from", type=int, required=True, help="Start week number")
    parser.add_argument("--week-to", type=int, required=True, help="End week number")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    agent = MostMotivatedStudentAgent(debug=args.debug)
    result = agent.run_analysis(week_from=args.week_from, week_to=args.week_to)
    print(result)

if __name__ == "__main__":
    main()