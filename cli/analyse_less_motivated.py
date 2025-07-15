import argparse
from agents.motivated_student_agent import MotivatedStudentAgent

def main():
    parser = argparse.ArgumentParser(description="Find the most motivated student in a week range")
    parser.add_argument("--week-from", type=int, required=True)
    parser.add_argument("--week-to", type=int, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    agent = MotivatedStudentAgent()
    result = agent.run_analysis('lowest', args.week_from, args.week_to, 3)

    print("\n" + "=" * 60)
    print("Most Motivated Student Analysis")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()