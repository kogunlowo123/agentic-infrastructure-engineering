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

variable "rag_corpus_bucket" {
  description = "Name of the RAG corpus GCS bucket"
  type        = string
}

variable "iac_templates_bucket" {
  description = "Name of the IaC templates GCS bucket"
  type        = string
}
