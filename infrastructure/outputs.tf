output "s3_bucket_name" {
  description = "Name of the S3 bucket storing scraped data"
  value       = aws_s3_bucket.scraper_data.bucket
}

output "sqs_queue_url" {
  description = "URL of the SQS task queue"
  value       = aws_sqs_queue.scraper_queue.url
}

output "sqs_dlq_url" {
  description = "URL of the dead letter queue"
  value       = aws_sqs_queue.scraper_dlq.url
}

output "lambda_function_name" {
  description = "Name of the Lambda scraper function"
  value       = aws_lambda_function.scraper.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda scraper function"
  value       = aws_lambda_function.scraper.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda logs"
  value       = aws_cloudwatch_log_group.scraper_logs.name
}
