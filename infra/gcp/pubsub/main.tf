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
  topics = ["iac-generated", "drift-detected", "cost-anomaly"]
}

resource "google_pubsub_topic" "topics" {
  for_each = toset(local.topics)

  name    = "${each.value}-${var.environment}"
  project = var.project_id

  message_retention_duration = "604800s" # 7 days

  labels = {
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_pubsub_topic" "dead_letter_topics" {
  for_each = toset(local.topics)

  name    = "${each.value}-${var.environment}-dlq"
  project = var.project_id

  message_retention_duration = "2592000s" # 30 days

  labels = {
    environment = var.environment
    managed-by  = "terraform"
    type        = "dead-letter"
  }
}

resource "google_pubsub_subscription" "subscriptions" {
  for_each = toset(local.topics)

  name    = "${each.value}-${var.environment}-sub"
  project = var.project_id
  topic   = google_pubsub_topic.topics[each.value].name

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"
  retain_acked_messages      = false

  expiration_policy {
    ttl = ""
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter_topics[each.value].id
    max_delivery_attempts = 5
  }

  labels = {
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "google_pubsub_topic_iam_member" "publisher" {
  for_each = toset(local.topics)

  project = var.project_id
  topic   = google_pubsub_topic.topics[each.value].name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.publisher_sa_email}"
}

resource "google_pubsub_subscription_iam_member" "subscriber" {
  for_each = toset(local.topics)

  project      = var.project_id
  subscription = google_pubsub_subscription.subscriptions[each.value].name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.subscriber_sa_email}"
}
