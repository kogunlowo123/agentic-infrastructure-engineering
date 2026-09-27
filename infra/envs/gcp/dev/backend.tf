terraform {
  backend "gcs" {
    bucket = "PROJECT_ID-terraform-states-dev"
    prefix = "terraform/state/dev"
  }
}
