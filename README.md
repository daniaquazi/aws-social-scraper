# AWS Social Media Scraper — FinOps Project

A serverless AWS pipeline that scrapes social media comments and profiles, built with cost efficiency as a first-class concern.

> **Status: In progress** — infrastructure and scraper code are being built out iteratively.

---

## Goal

Build a low-cost, production-style scraping pipeline on AWS while tracking and optimising cloud spend (FinOps). Target: keep monthly AWS costs under $30.

---

## Planned architecture

```
EventBridge (cron)
      │
      ▼
Amazon SQS (task queue)
      │
      ▼
AWS Lambda (scraper workers) ──► Target websites
      │
      ├──► S3 /raw        (raw HTML / JSON)
      │         │
      │         ▼
      └──► S3 /processed  (clean structured JSON)

CloudWatch  ◄──── metrics, logs, cost alarms
GitHub Actions ──► CI: lint, test, terraform validate
```

---

## Project structure

```
aws-social-scraper/
├── infrastructure/       # Terraform — coming soon
├── scraper/
│   └── requirements.txt  # Python dependencies
├── tests/                # coming soon
├── finops/
│   └── monthly-log.csv   # Estimated vs actual AWS costs
├── .github/
│   └── workflows/
│       └── ci.yml        # Lint, test, tf validate on push
└── README.md
```

---

## FinOps tracking

Monthly costs are logged in [`finops/monthly-log.csv`](./finops/monthly-log.csv) comparing estimated vs actual AWS spend, broken down by service.

| Service | Estimated monthly |
|---|---|
| Lambda | ~$0.20 |
| SQS | ~$0.00 (free tier) |
| S3 | ~$0.12 |
| CloudWatch | ~$3–8 |
| Data transfer | ~$5–15 |
| **Total** | **~$10–25/mo** |

---

## CI

GitHub Actions runs on every push to `main`:
- Python lint (flake8)
- pytest (with moto for AWS mocks)
- Terraform validate + format check

---

## Disclaimer

Always check a site's `robots.txt` and Terms of Service before scraping. This project is for personal learning and low-volume use only.

---

## License

MIT
