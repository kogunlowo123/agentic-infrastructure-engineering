output "service_account_emails" {
  description = "Map of service account names to emails"
  value       = { for k, v in google_service_account.accounts : k => v.email }
}

output "api_sa_email" {
  description = "Email of the API service account"
  value       = google_service_account.accounts["api-sa"].email
}

output "agent_runtime_sa_email" {
  description = "Email of the agent runtime service account"
  value       = google_service_account.accounts["agent-runtime-sa"].email
}

output "rag_core_sa_email" {
  description = "Email of the RAG core service account"
  value       = google_service_account.accounts["rag-core-sa"].email
}

output "build_sa_email" {
  description = "Email of the build service account"
  value       = google_service_account.accounts["build-sa"].email
}
