output "keyring_id" {
  description = "The ID of the KMS key ring"
  value       = google_kms_key_ring.keyring.id
}

output "database_key_id" {
  description = "The ID of the database encryption key"
  value       = google_kms_crypto_key.database_key.id
}

output "storage_key_id" {
  description = "The ID of the storage encryption key"
  value       = google_kms_crypto_key.storage_key.id
}

output "secrets_key_id" {
  description = "The ID of the secrets encryption key"
  value       = google_kms_crypto_key.secrets_key.id
}
