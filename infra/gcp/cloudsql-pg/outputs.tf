output "instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "instance_connection_name" {
  description = "Connection name for Cloud SQL proxy"
  value       = google_sql_database_instance.postgres.connection_name
}

output "private_ip_address" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = true
}

output "database_name" {
  description = "The name of the database"
  value       = google_sql_database.agentic_infra.name
}

output "database_user" {
  description = "The database user name"
  value       = google_sql_user.app_user.name
}

output "server_ca_cert" {
  description = "The server CA certificate"
  value       = google_sql_database_instance.postgres.server_ca_cert[0].cert
  sensitive   = true
}
