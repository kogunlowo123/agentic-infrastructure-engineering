output "network_id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.vpc.id
}

output "network_self_link" {
  description = "The self link of the VPC network"
  value       = google_compute_network.vpc.self_link
}

output "network_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "subnet_id" {
  description = "The ID of the main subnet"
  value       = google_compute_subnetwork.main.id
}

output "subnet_self_link" {
  description = "The self link of the main subnet"
  value       = google_compute_subnetwork.main.self_link
}

output "subnet_name" {
  description = "The name of the main subnet"
  value       = google_compute_subnetwork.main.name
}

output "pods_range_name" {
  description = "The name of the pods secondary IP range"
  value       = var.pods_range_name
}

output "services_range_name" {
  description = "The name of the services secondary IP range"
  value       = var.services_range_name
}

output "nat_ip" {
  description = "The NAT IP address"
  value       = google_compute_router_nat.nat.name
}
