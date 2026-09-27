output "bucket_names" {
  description = "Map of bucket logical names to actual bucket names"
  value       = { for k, v in google_storage_bucket.buckets : k => v.name }
}

output "bucket_urls" {
  description = "Map of bucket logical names to GCS URLs"
  value       = { for k, v in google_storage_bucket.buckets : k => v.url }
}

output "terraform_states_bucket" {
  description = "Name of the Terraform states bucket"
  value       = google_storage_bucket.buckets["terraform-states"].name
}

output "iac_templates_bucket" {
  description = "Name of the IaC templates bucket"
  value       = google_storage_bucket.buckets["iac-templates"].name
}

output "rag_corpus_bucket" {
  description = "Name of the RAG corpus bucket"
  value       = google_storage_bucket.buckets["rag-corpus"].name
}
