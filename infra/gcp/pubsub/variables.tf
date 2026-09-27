variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "publisher_sa_email" {
  description = "Service account email for publishing messages"
  type        = string
}

variable "subscriber_sa_email" {
  description = "Service account email for subscribing to messages"
  type        = string
}
