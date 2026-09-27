terraform {
  backend "gcs" {
    bucket = "PROJECT_ID-terraform-states-staging"
    prefix = "terraform/state/staging"
  }
}
