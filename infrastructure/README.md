# Infrastructure

Terraform configuration for all AWS resources.

## Files

- `main.tf` — EventBridge, SQS, Lambda, S3, CloudWatch, IAM
- `variables.tf` — region, project name, environment
- `outputs.tf` — queue URL, bucket names, Lambda ARN

## Usage

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
terraform destroy   # tear everything down
```

## Resources created

- EventBridge scheduler rule (hourly cron)
- SQS queue + dead-letter queue
- Lambda function (Python 3.11, reserved concurrency 5)
- IAM role + policy for Lambda
- S3 bucket (raw/ and processed/ prefixes, 30-day lifecycle on raw/)
- CloudWatch log group, dashboard, 429 alarm
- AWS Budget alert ($30/month threshold)
