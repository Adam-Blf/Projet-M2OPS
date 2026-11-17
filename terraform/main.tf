# Namespace, valeurs communes et Secrets.

locals {
  ns = kubernetes_namespace_v1.m2ops.metadata[0].name

  # Contexte de securite commun a tous les pods du projet
  pod_user = 1000
}

resource "kubernetes_namespace_v1" "m2ops" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "m2ops"
    }
  }
}

# Identifiants de la base, lus par PostgreSQL, la collecte et la purge.
resource "kubernetes_secret_v1" "db" {
  metadata {
    name      = "m2ops-db"
    namespace = local.ns
  }
  data = {
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
  }
}

# Mots de passe de Grafana, tires au hasard une fois puis gardes dans l'etat Terraform.
resource "random_password" "grafana_admin" {
  length  = 32
  special = false
}

resource "random_password" "grafana_db" {
  length  = 32
  special = false
}

resource "kubernetes_secret_v1" "grafana" {
  metadata {
    name      = "m2ops-grafana"
    namespace = local.ns
  }
  data = {
    GF_SECURITY_ADMIN_PASSWORD = random_password.grafana_admin.result
    GRAFANA_DB_PASSWORD        = random_password.grafana_db.result
  }
}
