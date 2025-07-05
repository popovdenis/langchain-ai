from services.student_motivation_service import StudentMotivationService
import argparse
import json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse student motivation.")
    parser.add_argument("--email", required=True, help="Student email")
    parser.add_argument("--week-from", type=int, required=True, help="Start week")
    parser.add_argument("--week-to", type=int, required=True, help="End week")
    args = parser.parse_args()

    service = StudentMotivationService()
    result = service.calculate_motivation(args.email, args.week_from, args.week_to)
    print(json.dumps(result, indent=2))