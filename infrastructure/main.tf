terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -------------------------------------------------------
# S3 — raw and processed buckets
# -------------------------------------------------------

resource "aws_s3_bucket" "scraper_data" {
  bucket = "${var.project_name}-data-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "scraper_data" {
  bucket = aws_s3_bucket.scraper_data.id

  rule {
    id     = "delete-raw-after-30-days"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "scraper_data" {
  bucket = aws_s3_bucket.scraper_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# -------------------------------------------------------
# SQS — task queue + dead letter queue
# -------------------------------------------------------

resource "aws_sqs_queue" "scraper_dlq" {
  name                      = "${var.project_name}-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

resource "aws_sqs_queue" "scraper_queue" {
  name                       = "${var.project_name}-queue-${var.environment}"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400 # 1 day

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.scraper_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

# -------------------------------------------------------
# IAM — Lambda role and policy
# -------------------------------------------------------

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.scraper_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.scraper_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# -------------------------------------------------------
# Lambda — scraper function
# -------------------------------------------------------

resource "aws_lambda_function" "scraper" {
  function_name    = "${var.project_name}-scraper-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  filename         = "${path.module}/lambda_package.zip"
  source_code_hash = fileexists("${path.module}/lambda_package.zip") ? filebase64sha256("${path.module}/lambda_package.zip") : null
  timeout          = 300
  memory_size      = 256

  environment {
    variables = {
      S3_BUCKET   = aws_s3_bucket.scraper_data.bucket
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.scraper_queue.arn
  function_name    = aws_lambda_function.scraper.arn
  batch_size       = 1
  enabled          = true
}

# -------------------------------------------------------
# EventBridge — hourly schedule
# -------------------------------------------------------

resource "aws_scheduler_schedule" "scraper_schedule" {
  name = "${var.project_name}-schedule-${var.environment}"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(1 hour)"

  target {
    arn      = aws_sqs_queue.scraper_queue.arn
    role_arn = aws_iam_role.eventbridge_role.arn

    input = jsonencode({
      source = "eventbridge-scheduler"
      task   = "scrape"
    })
  }
}

resource "aws_iam_role" "eventbridge_role" {
  name = "${var.project_name}-eventbridge-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  name = "${var.project_name}-eventbridge-policy-${var.environment}"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.scraper_queue.arn
    }]
  })
}

# -------------------------------------------------------
# CloudWatch — log group + 429 alarm
# -------------------------------------------------------

resource "aws_cloudwatch_log_group" "scraper_logs" {
  name              = "/aws/lambda/${aws_lambda_function.scraper.function_name}"
  retention_in_days = 14

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

resource "aws_cloudwatch_metric_alarm" "rate_limit_alarm" {
  alarm_name          = "${var.project_name}-rate-limit-alarm-${var.environment}"
  alarm_description   = "Triggers when scraper hits too many 429 rate limit errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RateLimitHit"
  namespace           = "Scraper"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
  }
}

# -------------------------------------------------------
# AWS Budget — alert at $20/month
# -------------------------------------------------------

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = "2"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
