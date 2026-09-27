terraform {
  required_version = ">= 1.8"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

locals {
  buckets = {
    terraform-states = {
      name_suffix  = "terraform-states"
      location     = var.region
      storage_class = "STANDARD"
    }
    iac-templates = {
      name_suffix  = "iac-templates"
      location     = var.region
      storage_class = "STANDARD"
    }
    rag-corpus = {
      name_suffix  = "rag-corpus"
      location     = var.region
      storage_class = "STANDARD"
    }
    build-artifacts = {
      name_suffix  = "build-artifacts"
      location     = var.region
      storage_class = "STANDARD"
    }
  }
}

resource "google_storage_bucket" "buckets" {
  for_each = local.buckets

  name          = "${var.project_id}-${each.value.name_suffix}-${var.environment}"
  project       = var.project_id
  location      = each.value.location
  storage_class = each.value.storage_class

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age        = 90
      with_state = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  encryption {
    default_kms_key_name = var.kms_key_id
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    platform    = "agentic-infra-engineering"
  }

  force_destroy = var.environment == "prod" ? false : true
}
