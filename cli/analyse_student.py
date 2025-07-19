import argparse
from agents.sudent_analysis_agent import StudentAnalysisAgent

def main():
    parser = argparse.ArgumentParser(description="Find the most motivated student in a week range")
    parser.add_argument("--email", type=str, required=True)
    parser.add_argument("--week-from", type=int, required=True)
    parser.add_argument("--week-to", type=int, required=True)
    args = parser.parse_args()

    agent = StudentAnalysisAgent()
    result = agent.run_analysis(args.email,args. week_from, args.week_to)

    print("\n" + "=" * 60)
    print("Student Analysis")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()