import boto3
import csv
import json
from datetime import datetime, timedelta


def get_monthly_costs(start_date, end_date):
    """
    Pull actual AWS costs from Cost Explorer API
    broken down by service.
    """
    client = boto3.client("ce", region_name="us-east-1")

    response = client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date,
            "End": end_date
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"}
        ],
        Filter={
            "Tags": {
                "Key": "Project",
                "Values": ["aws-social-scraper"]
            }
        }
    )

    results = []
    for period in response["ResultsByTime"]:
        month = period["TimePeriod"]["Start"][:7]
        for group in period["Groups"]:
            service = group["Keys"][0]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if cost > 0:
                results.append({
                    "month": month,
                    "service": service,
                    "actual_cost_usd": round(cost, 4)
                })

    return results


def get_estimated_costs():
    """
    Return our estimated costs per service
    based on expected usage.
    """
    return {
        "AWS Lambda": 0.20,
        "Amazon SQS": 0.00,
        "Amazon S3": 0.12,
        "Amazon EventBridge": 0.00,
        "Amazon CloudWatch": 5.00,
        "AWS Data Transfer": 10.00,
    }


def save_to_csv(costs, filename="finops/monthly-log.csv"):
    """
    Save cost report to CSV comparing
    estimated vs actual costs.
    """
    estimates = get_estimated_costs()

    fieldnames = [
        "month",
        "service",
        "estimated_cost_usd",
        "actual_cost_usd",
        "variance_usd",
        "variance_pct"
    ]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for cost in costs:
            service = cost["service"]
            actual = cost["actual_cost_usd"]
            estimated = estimates.get(service, 0)
            variance = round(actual - estimated, 4)
            variance_pct = round((variance / estimated * 100), 1) if estimated > 0 else 0

            writer.writerow({
                "month": cost["month"],
                "service": service,
                "estimated_cost_usd": estimated,
                "actual_cost_usd": actual,
                "variance_usd": variance,
                "variance_pct": f"{variance_pct}%"
            })

    print(f"Cost report saved to {filename}")


def print_summary(costs):
    """Print a summary of costs to the terminal."""
    total_actual = sum(c["actual_cost_usd"] for c in costs)
    total_estimated = sum(get_estimated_costs().values())

    print("\n" + "=" * 50)
    print("AWS COST REPORT — aws-social-scraper")
    print("=" * 50)

    for cost in costs:
        print(f"  {cost['service']:<35} ${cost['actual_cost_usd']:.4f}")

    print("-" * 50)
    print(f"  {'Total actual':<35} ${total_actual:.4f}")
    print(f"  {'Total estimated':<35} ${total_estimated:.2f}")
    print(f"  {'Variance':<35} ${round(total_actual - total_estimated, 4):.4f}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    today = datetime.today()
    first_of_month = today.replace(day=1).strftime("%Y-%m-%d")
    tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Fetching costs from {first_of_month} to {today.strftime('%Y-%m-%d')}...")

    costs = get_monthly_costs(first_of_month, tomorrow)

    if not costs:
        print("No tagged costs found yet — have you run terraform apply?")
        print("Make sure all resources have the tag: Project = aws-social-scraper")
    else:
        print_summary(costs)
        save_to_csv(costs)
