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
  service_accounts = {
    api-sa            = { display_name = "API Service Account" }
    agent-runtime-sa  = { display_name = "Agent Runtime Service Account" }
    rag-core-sa       = { display_name = "RAG Core Service Account" }
    build-sa          = { display_name = "Build Service Account" }
  }
}

resource "google_service_account" "accounts" {
  for_each = local.service_accounts

  account_id   = "${each.key}-${var.environment}"
  display_name = each.value.display_name
  project      = var.project_id
  description  = "${each.value.display_name} for ${var.environment} environment"
}

# Cloud SQL client access
resource "google_project_iam_member" "cloudsql_client" {
  for_each = toset(["api-sa", "agent-runtime-sa", "rag-core-sa"])

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.accounts[each.value].email}"
}

# GCS access
resource "google_storage_bucket_iam_member" "rag_corpus_reader" {
  bucket = var.rag_corpus_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.accounts["rag-core-sa"].email}"
}

resource "google_storage_bucket_iam_member" "rag_corpus_writer" {
  bucket = var.rag_corpus_bucket
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.accounts["rag-core-sa"].email}"
}

resource "google_storage_bucket_iam_member" "iac_templates_reader" {
  bucket = var.iac_templates_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.accounts["agent-runtime-sa"].email}"
}

# Pub/Sub access
resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.accounts["agent-runtime-sa"].email}"
}

resource "google_project_iam_member" "pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.accounts["agent-runtime-sa"].email}"
}

# Secret Manager access
resource "google_project_iam_member" "secret_accessor" {
  for_each = toset(["api-sa", "agent-runtime-sa", "rag-core-sa"])

  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.accounts[each.value].email}"
}

# Vertex AI access
resource "google_project_iam_member" "vertex_ai_user" {
  for_each = toset(["agent-runtime-sa", "rag-core-sa"])

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.accounts[each.value].email}"
}

# Workload Identity bindings for GKE
resource "google_service_account_iam_member" "workload_identity" {
  for_each = {
    "api-sa"           = "api"
    "agent-runtime-sa" = "agent-runtime"
    "rag-core-sa"      = "rag-core"
  }

  service_account_id = google_service_account.accounts[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/${each.value}]"
}

# Build SA - Artifact Registry writer
resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.accounts["build-sa"].email}"
}
