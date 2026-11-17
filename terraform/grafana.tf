# Grafana : tableaux de bord sur la base, en lecture seule.
# Acces : http://servemilien:30300 (NodePort ; Traefik est desactive dans k3s).
# Source de donnees et tableau de bord : fichiers de terraform/grafana/ (provisioning).

locals {
  grafana_files = {
    datasources = "${path.module}/grafana/datasources.yaml"
    provider    = "${path.module}/grafana/dashboards.yaml"
    dashboard   = "${path.module}/grafana/m2ops-articles.json"
  }
  grafana_role_sql = file("${path.module}/sql/grafana_ro.sql")

  # Empreinte des fichiers de provisioning : si l'un change, le pod Grafana est recree.
  grafana_checksum = sha256(join("", [for f in values(local.grafana_files) : file(f)]))
}

# --- Role PostgreSQL grafana_ro ---------------------------------------------

resource "kubernetes_config_map_v1" "grafana_role_sql" {
  metadata {
    name      = "grafana-role-sql"
    namespace = local.ns
  }
  data = {
    "grafana_ro.sql" = local.grafana_role_sql
  }
}

# Job lance une fois : psql cree ou met a jour le role. Son nom contient une empreinte du
# script et du mot de passe : si l'un change, Terraform remplace le Job, qui se relance.
resource "kubernetes_job_v1" "grafana_role" {
  metadata {
    name      = "grafana-role-${substr(sha256("${local.grafana_role_sql}${random_password.grafana_db.result}"), 0, 8)}"
    namespace = local.ns
    labels = {
      "app.kubernetes.io/name" = "grafana-role"
    }
  }

  spec {
    backoff_limit = 3

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name"    = "grafana-role"
          "app.kubernetes.io/part-of" = "m2ops"
        }
      }

      spec {
        restart_policy = "Never"
        # pas de jeton d'API Kubernetes ni de variables d'environnement des autres Services
        automount_service_account_token = false
        enable_service_links            = false


        security_context {
          run_as_non_root = true
          run_as_user     = 70 # utilisateur postgres de l'image alpine
          run_as_group    = 70
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }

        container {
          name  = "psql"
          image = var.postgres_image
          # $(VAR) est remplace par Kubernetes au demarrage : le mot de passe n'apparait pas
          # dans la description du pod.
          command = [
            "psql", "-v", "ON_ERROR_STOP=1",
            "-v", "pw=$(GRAFANA_DB_PASSWORD)",
            "-v", "db=$(PGDATABASE)",
            "-f", "/sql/grafana_ro.sql",
          ]

          env {
            name  = "PGHOST"
            value = kubernetes_service_v1.db.metadata[0].name
          }
          env {
            name = "PGDATABASE"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.db.metadata[0].name
                key  = "POSTGRES_DB"
              }
            }
          }
          env {
            name = "PGUSER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.db.metadata[0].name
                key  = "POSTGRES_USER"
              }
            }
          }
          env {
            name = "PGPASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.db.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }
          env {
            name = "GRAFANA_DB_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.grafana.metadata[0].name
                key  = "GRAFANA_DB_PASSWORD"
              }
            }
          }

          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }

          volume_mount {
            name       = "sql"
            mount_path = "/sql"
            read_only  = true
          }
        }

        volume {
          name = "sql"
          config_map {
            name = kubernetes_config_map_v1.grafana_role_sql.metadata[0].name
          }
        }
      }
    }
  }

  wait_for_completion = true
  timeouts {
    create = "3m"
  }
}

# --- Provisioning -----------------------------------------------------------

resource "kubernetes_config_map_v1" "grafana_datasources" {
  metadata {
    name      = "grafana-datasources"
    namespace = local.ns
  }
  data = {
    "datasources.yaml" = file(local.grafana_files.datasources)
  }
}

resource "kubernetes_config_map_v1" "grafana_dashboards_provider" {
  metadata {
    name      = "grafana-dashboards-provider"
    namespace = local.ns
  }
  data = {
    "dashboards.yaml" = file(local.grafana_files.provider)
  }
}

resource "kubernetes_config_map_v1" "grafana_dashboards" {
  metadata {
    name      = "grafana-dashboards"
    namespace = local.ns
  }
  data = {
    "m2ops-articles.json" = file(local.grafana_files.dashboard)
  }
}

# --- Service et Deployment ----------------------------------------------------

resource "kubernetes_service_v1" "grafana" {
  metadata {
    name      = "grafana"
    namespace = local.ns
    labels = {
      "app.kubernetes.io/name" = "grafana"
    }
  }
  spec {
    type = "NodePort"
    selector = {
      "app.kubernetes.io/name" = "grafana"
    }
    port {
      name        = "http"
      port        = 3000
      target_port = "http"
      node_port   = var.grafana_node_port
    }
  }
}

resource "kubernetes_deployment_v1" "grafana" {
  metadata {
    name      = "grafana"
    namespace = local.ns
    labels = {
      "app.kubernetes.io/name" = "grafana"
    }
  }

  spec {
    replicas = 1
    strategy {
      type = "Recreate" # un seul pod a la fois sur grafana.db (SQLite)
    }

    selector {
      match_labels = {
        "app.kubernetes.io/name" = "grafana"
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name"    = "grafana"
          "app.kubernetes.io/part-of" = "m2ops"
        }
        annotations = {
          "m2ops/provisioning-checksum" = local.grafana_checksum
        }
      }

      spec {
        automount_service_account_token = false
        enable_service_links            = false

        security_context {
          run_as_non_root = true
          run_as_user     = local.pod_user
          run_as_group    = local.pod_user
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }

        container {
          name  = "grafana"
          image = var.grafana_image

          port {
            name           = "http"
            container_port = 3000
          }

          # GF_SECURITY_ADMIN_PASSWORD et GRAFANA_DB_PASSWORD
          env_from {
            secret_ref {
              name = kubernetes_secret_v1.grafana.metadata[0].name
            }
          }

          dynamic "env" {
            for_each = {
              GF_SECURITY_ADMIN_USER                    = "admin"
              GF_SERVER_ROOT_URL                        = var.grafana_root_url
              GF_DATE_FORMATS_DEFAULT_TIMEZONE          = var.timezone
              GF_USERS_ALLOW_SIGN_UP                    = "false"
              GF_AUTH_ANONYMOUS_ENABLED                 = "false"
              GF_ANALYTICS_REPORTING_ENABLED            = "false"
              GF_ANALYTICS_CHECK_FOR_UPDATES            = "false"
              GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES     = "false"
              GF_NEWS_NEWS_FEED_ENABLED                 = "false"
              GF_PLUGINS_PREINSTALL_DISABLED            = "true"
              GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH = "/etc/grafana/dashboards/m2ops-articles.json"
            }
            content {
              name  = env.key
              value = env.value
            }
          }

          readiness_probe {
            http_get {
              path = "/api/health"
              port = "http"
            }
            initial_delay_seconds = 10
            period_seconds        = 10
          }
          liveness_probe {
            http_get {
              path = "/api/health"
              port = "http"
            }
            initial_delay_seconds = 60
            period_seconds        = 30
            failure_threshold     = 5
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "128Mi"
            }
            limits = {
              memory = "384Mi"
            }
          }

          security_context {
            allow_privilege_escalation = false
            capabilities {
              drop = ["ALL"]
            }
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/grafana"
          }
          volume_mount {
            name       = "datasources"
            mount_path = "/etc/grafana/provisioning/datasources"
            read_only  = true
          }
          volume_mount {
            name       = "dashboards-provider"
            mount_path = "/etc/grafana/provisioning/dashboards"
            read_only  = true
          }
          volume_mount {
            name       = "dashboards"
            mount_path = "/etc/grafana/dashboards"
            read_only  = true
          }
        }

        volume {
          name = "data"
          host_path {
            path = "${var.appdata_dir}/grafana"
            type = "Directory" # cree a la main, proprietaire 1000:1000
          }
        }
        volume {
          name = "datasources"
          config_map {
            name = kubernetes_config_map_v1.grafana_datasources.metadata[0].name
          }
        }
        volume {
          name = "dashboards-provider"
          config_map {
            name = kubernetes_config_map_v1.grafana_dashboards_provider.metadata[0].name
          }
        }
        volume {
          name = "dashboards"
          config_map {
            name = kubernetes_config_map_v1.grafana_dashboards.metadata[0].name
          }
        }
      }
    }
  }

  # Le role grafana_ro doit exister avant que Grafana interroge la base
  depends_on = [kubernetes_job_v1.grafana_role]
}
