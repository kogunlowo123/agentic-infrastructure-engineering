terraform {
  backend "gcs" {
    bucket = "PROJECT_ID-terraform-states-prod"
    prefix = "terraform/state/prod"
  }
}
