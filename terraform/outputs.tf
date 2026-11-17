output "grafana_url" {
  description = "Adresse de Grafana"
  value       = var.grafana_root_url
}

output "grafana_admin_password" {
  description = "Mot de passe du compte admin de Grafana (terraform output -raw grafana_admin_password)"
  value       = random_password.grafana_admin.result
  sensitive   = true
}
