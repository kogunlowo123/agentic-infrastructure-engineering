output "topic_ids" {
  description = "Map of topic logical names to topic IDs"
  value       = { for k, v in google_pubsub_topic.topics : k => v.id }
}

output "subscription_ids" {
  description = "Map of subscription logical names to subscription IDs"
  value       = { for k, v in google_pubsub_subscription.subscriptions : k => v.id }
}

output "iac_generated_topic" {
  description = "Full topic ID for iac-generated events"
  value       = google_pubsub_topic.topics["iac-generated"].id
}

output "drift_detected_topic" {
  description = "Full topic ID for drift-detected events"
  value       = google_pubsub_topic.topics["drift-detected"].id
}

output "cost_anomaly_topic" {
  description = "Full topic ID for cost-anomaly events"
  value       = google_pubsub_topic.topics["cost-anomaly"].id
}
