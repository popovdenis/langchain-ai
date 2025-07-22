import argparse
from agents.dropout_risk_agent import DropoutRiskAgent

def main():
    parser = argparse.ArgumentParser(description="Find the most motivated student in a week range")
    parser.add_argument("--week-from", type=int, required=True)
    parser.add_argument("--week-to", type=int, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    agent = DropoutRiskAgent()
    result = agent.run_analysis('highest', args.week_from, args.week_to, 5)

    print("\n" + "=" * 60)
    print("Most Motivated Student Analysis")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()