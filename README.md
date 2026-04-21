# AWS Social Scraper — FinOps Project

A serverless AWS pipeline that scrapes Hacker News tech discussions and stores structured data in S3, built with cost efficiency as a first-class concern.

![CI](https://github.com/daniaquazi/aws-social-scraper/actions/workflows/ci.yml/badge.svg)

---

## What it does

Scrapes the top stories and comments from Hacker News (via the Algolia API) every hour, cleans and structures the data, and stores it in Amazon S3 — all automatically, serverlessly, and at minimal cost.

- Fetches top AI and tech stories + comments
- Cleans HTML, filters deleted/short comments, adds word counts
- Stores raw and processed JSON in S3 with date-partitioned paths
- Monitors for rate limiting via CloudWatch alarms
- Tracks actual vs estimated costs monthly in `finops/monthly-log.csv`

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│   EventBridge   │────►│   Amazon SQS    │────►│    AWS Lambda       │
│  Hourly cron    │     │ Queue + DLQ     │     │  Python 3.11        │
└─────────────────┘     └─────────────────┘     └──────────┬──────────┘
                                                            │
                                              ┌─────────────▼─────────────┐
                                              │   Hacker News Algolia API │
                                              │   Stories + comments      │
                                              └───────────────────────────┘
                                                            │
                               ┌────────────────────────────┤
                               │                            │
                    ┌──────────▼──────────┐      ┌─────────▼───────────┐
                    │    S3 — raw/        │      │   S3 — processed/   │
                    │ Raw JSON (30d TTL)  │─────►│  Clean JSON         │
                    └─────────────────────┘      └─────────────────────┘

CloudWatch ◄─── Lambda logs, metrics, 429 rate limit alarms
GitHub Actions ──► CI: lint, test, terraform validate on every push
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Scheduler | Amazon EventBridge |
| Queue | Amazon SQS + Dead Letter Queue |
| Compute | AWS Lambda (Python 3.11) |
| Storage | Amazon S3 (lifecycle rules on raw/) |
| Monitoring | Amazon CloudWatch |
| Infrastructure as Code | Terraform |
| CI/CD | GitHub Actions |
| Data source | Hacker News via Algolia API |

---

## Project structure

```
aws-social-scraper/
├── infrastructure/
│   ├── main.tf           # All AWS resources
│   ├── variables.tf      # Region, env, project name
│   └── outputs.tf        # Queue URL, bucket names
├── scraper/
│   ├── handler.py        # Lambda entry point
│   ├── scraper.py        # Algolia API + backoff logic
│   ├── parser.py         # HTML cleaning, data structuring
│   └── requirements.txt
├── tests/
│   ├── conftest.py       # pytest path config
│   └── test_handler.py   # Unit tests with mocks
├── finops/
│   ├── cost_report.py    # AWS Cost Explorer API script
│   └── monthly-log.csv   # Estimated vs actual costs
├── .github/
│   └── workflows/
│       └── ci.yml        # Lint, test, tf validate on push
└── README.md
```

---

## FinOps cost analysis

### Architecture decisions driven by cost

**Lambda over EC2/ECS Fargate:**
EC2 and Fargate run continuously — even when idle. For a scraper that runs once per hour, this wastes ~23 hours of compute per day. Lambda charges only per invocation (200ms average) making it ~99% cheaper for this workload.

**Single S3 bucket over multiple storage layers:**
The original design used both S3 and DynamoDB. DynamoDB adds cost with no benefit for append-only scrape data. S3 alone handles both raw and processed data with a simple prefix structure.

**Lifecycle rules on raw data:**
Raw JSON is only needed for reprocessing. A 30-day lifecycle rule on the `raw/` prefix automatically deletes old files, keeping storage costs near zero.

**SQS as rate limiter:**
Instead of complex throttling code, SQS naturally limits concurrency. Combined with Lambda's batch size of 1, this prevents hammering the API and avoids rate limit costs.

### Pre-deployment cost estimate

> Actual costs will be tracked in [`finops/monthly-log.csv`](./finops/monthly-log.csv) once the pipeline has been running for a full month. The figures below are pre-deployment estimates based on AWS pricing documentation.

| Service | Reason | Estimated/mo |
|---|---|---|
| Lambda | ~720 invocations/month (hourly) | ~$0.00 (free tier) |
| SQS | ~720 messages/month | ~$0.00 (free tier) |
| S3 | ~1GB stored, lifecycle managed | ~$0.02 |
| EventBridge | Scheduled rules | ~$0.00 (free tier) |
| CloudWatch | Logs + alarm | ~$3–5 |
| Data transfer | Outbound API calls | ~$1–3 |
| **Total** | | **~$4–8/mo** |

All resources are tagged for cost attribution:

```
Project     = aws-social-scraper
Environment = prod
Owner       = dania
```

A AWS Budget alert triggers at 80% of $2/month — ensuring no surprise charges.

---

## Rate limiting strategy

- Exponential backoff with jitter on 429/503 responses
- Random human-like delays between requests (0.5–1.5s)
- SQS visibility timeout as automatic retry on failure
- CloudWatch alarm if `RateLimitHit > 10` in a 5-minute window

---

## CI

GitHub Actions runs on every push to `main`:
- Python lint (flake8)
- pytest unit tests with mocked AWS and API calls
- Terraform validate + format check

---

## Deployment

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

Tear down:
```bash
aws s3 rm s3://aws-social-scraper-data-prod --recursive
terraform destroy
```

---

## Disclaimer

This project uses the public Hacker News Algolia API which is free and openly available. Always check a site's terms of service before scraping.

---

## License

MIT
