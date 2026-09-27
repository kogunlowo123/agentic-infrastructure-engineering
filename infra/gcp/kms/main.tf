terraform {
  required_version = ">= 1.8"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_kms_key_ring" "keyring" {
  name     = "agentic-infra-${var.environment}"
  project  = var.project_id
  location = var.region
}

resource "google_kms_crypto_key" "database_key" {
  name     = "database-key"
  key_ring = google_kms_key_ring.keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    key-type    = "database"
  }

  destroy_scheduled_duration = "86400s" # 1 day minimum for destroy
}

resource "google_kms_crypto_key" "storage_key" {
  name     = "storage-key"
  key_ring = google_kms_key_ring.keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    key-type    = "storage"
  }

  destroy_scheduled_duration = "86400s"
}

resource "google_kms_crypto_key" "secrets_key" {
  name     = "secrets-key"
  key_ring = google_kms_key_ring.keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    key-type    = "secrets"
  }

  destroy_scheduled_duration = "86400s"
}
