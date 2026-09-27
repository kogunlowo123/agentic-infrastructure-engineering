variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the GKE cluster"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "network_id" {
  description = "VPC network ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the GKE cluster"
  type        = string
}

variable "pods_range_name" {
  description = "Name of the pods secondary IP range"
  type        = string
}

variable "services_range_name" {
  description = "Name of the services secondary IP range"
  type        = string
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master nodes"
  type        = string
  default     = "172.16.0.0/28"
}

variable "master_authorized_cidr_blocks" {
  description = "List of CIDR blocks authorized to access the master"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "min_node_count" {
  description = "Minimum number of app nodes"
  type        = number
  default     = 2
}

variable "max_node_count" {
  description = "Maximum number of app nodes"
  type        = number
  default     = 10
}

variable "app_machine_type" {
  description = "Machine type for app nodes"
  type        = string
  default     = "n2-standard-8"
}

variable "system_node_sa_email" {
  description = "Service account email for system node pool"
  type        = string
}

variable "app_node_sa_email" {
  description = "Service account email for app node pool"
  type        = string
}
