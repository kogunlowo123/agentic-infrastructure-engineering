package infra_engineering

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# Allow health checks for anyone
allow if {
    input.path == "/api/v1/health"
}

allow if {
    input.path == "/api/v1/readiness"
}

# IaC generation requires T2 tier and explicit approval scope
allow if {
    input.path == "/api/v1/iac/generate"
    input.method == "POST"
    input.user.tier == "T2"
    "iac:generate" in input.user.scopes
}

# PR status check requires authenticated user
allow if {
    startswith(input.path, "/api/v1/iac/")
    input.method == "GET"
    input.user.id != ""
    input.user.tenant_id == input.resource.tenant_id
}

# Drift detection requires at least T1
allow if {
    input.path == "/api/v1/drift/detect"
    input.method == "POST"
    input.user.tier in ["T1", "T2"]
}

# Cost forecast requires at least T1
allow if {
    input.path == "/api/v1/cost/forecast"
    input.method == "GET"
    input.user.tier in ["T1", "T2"]
}

# Deny access to other tenants' resources
deny_cross_tenant if {
    input.resource.tenant_id != ""
    input.user.tenant_id != input.resource.tenant_id
}

# Deny blocked resource types
deny_blocked_resource if {
    input.request.resource_type in blocked_resource_types
}

blocked_resource_types := {
    "google_compute_instance_with_external_ip",
}

# Aggregate deny rules
violation[msg] if {
    deny_cross_tenant
    msg := "Cross-tenant resource access denied"
}

violation[msg] if {
    deny_blocked_resource
    msg := concat("", ["Resource type ", input.request.resource_type, " is blocked by policy"])
}
