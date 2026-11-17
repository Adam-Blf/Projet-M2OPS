# Les deux taches planifiees : collecte (7 h) et purge (7 h 30), heure de Paris.
# Meme image, meme securite, memes volumes : un seul bloc decrit les deux (for_each),
# seules les valeurs de local.jobs changent.
#
# Lancer une collecte a la main sans attendre 7 h :
#   kubectl -n m2ops create job --from=cronjob/collector collect-test

locals {
  jobs = {
    collector = {
      schedule = var.collect_schedule
      args     = concat(["python", "-m", "src.collect"], flatten([for s in var.sources : ["--source", s]]))
      env      = {}
      deadline = 600 # collecte bloquee -> arretee apres 10 min
      memory   = "256Mi"
    }
    purge = {
      schedule = var.purge_schedule
      args     = ["python", "-m", "src.purge"]
      env      = { RETENTION_DAYS = tostring(var.retention_days) }
      deadline = 300
      memory   = "128Mi"
    }
  }
}

resource "kubernetes_cron_job_v1" "job" {
  for_each = local.jobs

  metadata {
    name      = each.key
    namespace = local.ns
    labels = {
      "app.kubernetes.io/name" = each.key
    }
  }

  spec {
    schedule                      = each.value.schedule
    timezone                      = var.timezone
    concurrency_policy            = "Forbid" # jamais deux executions en meme temps
    starting_deadline_seconds     = 3600     # rattrapage si le serveur etait indisponible (1 h max)
    successful_jobs_history_limit = 3
    failed_jobs_history_limit     = 3

    job_template {
      metadata {}
      spec {
        backoff_limit           = 1 # un seul nouvel essai
        active_deadline_seconds = each.value.deadline

        template {
          metadata {
            labels = {
              "app.kubernetes.io/name"    = each.key
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
              run_as_user     = local.pod_user
              run_as_group    = local.pod_user
              seccomp_profile {
                type = "RuntimeDefault"
              }
            }

            container {
              name              = each.key
              image             = var.collector_image
              image_pull_policy = var.collector_image_pull_policy
              args              = each.value.args

              env_from {
                secret_ref {
                  name = kubernetes_secret_v1.db.metadata[0].name
                }
              }
              env {
                name  = "POSTGRES_HOST"
                value = kubernetes_service_v1.db.metadata[0].name
              }
              dynamic "env" {
                for_each = each.value.env
                content {
                  name  = env.key
                  value = env.value
                }
              }

              resources {
                requests = {
                  cpu    = "50m"
                  memory = "64Mi"
                }
                limits = {
                  memory = each.value.memory
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
                name       = "data"
                mount_path = "/app/data"
              }
              volume_mount {
                name       = "tmp"
                mount_path = "/tmp"
              }
            }

            volume {
              name = "data"
              host_path {
                path = "${var.appdata_dir}/data"
                type = "Directory" # doit exister et appartenir a 1000:1000
              }
            }
            volume {
              name = "tmp"
              empty_dir {}
            }
          }
        }
      }
    }
  }
}
