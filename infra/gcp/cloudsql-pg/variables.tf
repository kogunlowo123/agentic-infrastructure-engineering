variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the Cloud SQL instance"
  type        = string
  default     = "us-central1"
}

variable "instance_name" {
  description = "Name prefix for the Cloud SQL instance"
  type        = string
  default     = "agentic-infra-pg"
}

variable "tier" {
  description = "Machine tier for Cloud SQL"
  type        = string
  default     = "db-custom-4-16384"
}

variable "disk_size_gb" {
  description = "Initial disk size in GB"
  type        = number
  default     = 100
}

variable "network_id" {
  description = "VPC network ID for private IP"
  type        = string
}

variable "db_password" {
  description = "Password for the database user"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}
