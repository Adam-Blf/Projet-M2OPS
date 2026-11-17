# Base PostgreSQL permanente : Service "db" + StatefulSet a 1 replique.
# Donnees : <appdata_dir>/postgres sur le serveur (hostPath).

resource "kubernetes_service_v1" "db" {
  metadata {
    name      = "db"
    namespace = local.ns
    labels = {
      "app.kubernetes.io/name" = "postgres"
    }
  }
  spec {
    selector = {
      "app.kubernetes.io/name" = "postgres"
    }
    port {
      name        = "postgres"
      port        = 5432
      target_port = 5432
    }
  }
}

resource "kubernetes_stateful_set_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = local.ns
    labels = {
      "app.kubernetes.io/name" = "postgres"
    }
  }

  spec {
    service_name = kubernetes_service_v1.db.metadata[0].name
    replicas     = 1

    selector {
      match_labels = {
        "app.kubernetes.io/name" = "postgres"
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name"    = "postgres"
          "app.kubernetes.io/part-of" = "m2ops"
        }
      }

      spec {
        # pas de jeton d'API Kubernetes ni de variables d'environnement des autres Services
        automount_service_account_token = false
        enable_service_links            = false

        container {
          name  = "postgres"
          image = var.postgres_image

          env_from {
            secret_ref {
              name = kubernetes_secret_v1.db.metadata[0].name
            }
          }
          # sous-dossier : PostgreSQL refuse un dossier de donnees non vide
          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }

          port {
            container_port = 5432
          }

          readiness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
          liveness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            }
            initial_delay_seconds = 30
            period_seconds        = 30
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
            limits = {
              memory = "512Mi"
            }
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }
        }

        volume {
          name = "data"
          host_path {
            path = "${var.appdata_dir}/postgres"
            type = "DirectoryOrCreate"
          }
        }
      }
    }
  }
}
