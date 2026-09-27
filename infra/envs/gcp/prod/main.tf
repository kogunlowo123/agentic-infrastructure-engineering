terraform {
  required_version = ">= 1.8"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  environment  = "prod"
  network_name = "agentic-infra-prod"
}

module "network" {
  source = "../../../gcp/network"

  project_id          = var.project_id
  region              = var.region
  network_name        = local.network_name
  environment         = local.environment
  subnet_cidr         = "10.20.0.0/24"
  pods_cidr           = "10.21.0.0/16"
  services_cidr       = "10.22.0.0/20"
  pods_range_name     = "gke-pods"
  services_range_name = "gke-services"
}

module "kms" {
  source = "../../../gcp/kms"

  project_id  = var.project_id
  region      = var.region
  environment = local.environment
}

module "gcs" {
  source = "../../../gcp/gcs"

  project_id  = var.project_id
  region      = var.region
  environment = local.environment
  kms_key_id  = module.kms.storage_key_id
}

module "iam" {
  source = "../../../gcp/iam"

  project_id           = var.project_id
  environment          = local.environment
  rag_corpus_bucket    = module.gcs.rag_corpus_bucket
  iac_templates_bucket = module.gcs.iac_templates_bucket
}

module "cloudsql" {
  source = "../../../gcp/cloudsql-pg"

  project_id   = var.project_id
  region       = var.region
  environment  = local.environment
  network_id   = module.network.network_id
  db_password  = var.db_password
  tier         = "db-custom-8-32768"
  disk_size_gb = 200
}

module "pubsub" {
  source = "../../../gcp/pubsub"

  project_id          = var.project_id
  environment         = local.environment
  publisher_sa_email  = module.iam.agent_runtime_sa_email
  subscriber_sa_email = module.iam.agent_runtime_sa_email
}

module "gke" {
  source = "../../../gcp/gke"

  project_id              = var.project_id
  region                  = var.region
  cluster_name            = "agentic-infra-prod"
  network_id              = module.network.network_id
  subnet_id               = module.network.subnet_id
  pods_range_name         = module.network.pods_range_name
  services_range_name     = module.network.services_range_name
  environment             = local.environment
  min_node_count          = 3
  max_node_count          = 10
  app_machine_type        = "n2-standard-8"
  system_node_sa_email    = module.iam.api_sa_email
  app_node_sa_email       = module.iam.agent_runtime_sa_email
  master_ipv4_cidr_block  = "172.16.2.0/28"
}
