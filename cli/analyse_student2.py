import argparse
from agents.student_motivation_agent import analyze_student

def main():
    parser = argparse.ArgumentParser(description="Analyse student motivation")
    parser.add_argument("--email", required=True, help="Student email")
    parser.add_argument("--week-from", type=int, required=True, help="Start week")
    parser.add_argument("--week-to", type=int, required=True, help="End week")

    args = parser.parse_args()

    try:
        result = analyze_student(args.email, args.week_from, args.week_to)
        for row in result:
            print(f"{row['label']}: {row['value']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()