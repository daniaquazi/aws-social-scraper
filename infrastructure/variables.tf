variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Name of the project, used for naming all resources"
  type        = string
  default     = "aws-social-scraper"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "owner" {
  description = "Your name, used for resource tags"
  type        = string
  default     = "dania"
}

variable "alert_email" {
  description = "Email address for budget and alarm alerts"
  type        = string
  default     = "your-email@example.com"
}
