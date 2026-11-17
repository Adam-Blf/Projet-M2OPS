# Parametres du deploiement. Les valeurs par defaut correspondent au serveur du projet ;
# les identifiants PostgreSQL viennent de .env (bin/tf les passe en TF_VAR_*).

variable "kubeconfig_path" {
  description = "Fichier kubeconfig du cluster k3s"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Namespace Kubernetes du projet"
  type        = string
  default     = "m2ops"
}

variable "appdata_dir" {
  description = "Dossier du serveur qui recoit les donnees (postgres/, data/, grafana/)"
  type        = string
  default     = "/srv/appdata/m2ops"
}

# --- PostgreSQL -------------------------------------------------------------

variable "postgres_image" {
  type    = string
  default = "docker.io/library/postgres:16-alpine"
}

variable "postgres_db" {
  description = "Nom de la base (POSTGRES_DB du .env)"
  type        = string
}

variable "postgres_user" {
  description = "Proprietaire de la base (POSTGRES_USER du .env)"
  type        = string
}

variable "postgres_password" {
  description = "Mot de passe de postgres_user (POSTGRES_PASSWORD du .env)"
  type        = string
  sensitive   = true
}

# --- Collecte et purge ------------------------------------------------------

variable "collector_image" {
  description = "Image de la collecte et de la purge"
  type        = string
  default     = "localhost/m2ops-collector:0.1"
}

variable "collector_image_pull_policy" {
  description = "Never tant que l'image est importee a la main ; Always avec ghcr.io"
  type        = string
  default     = "Never"
}

variable "timezone" {
  type    = string
  default = "Europe/Paris"
}

variable "collect_schedule" {
  description = "Heure de la collecte (format cron, heure de Paris)"
  type        = string
  default     = "0 7 * * *"
}

variable "purge_schedule" {
  description = "Heure de la purge (format cron, heure de Paris)"
  type        = string
  default     = "30 7 * * *"
}

variable "retention_days" {
  description = "Nombre de jours conserves avant purge"
  type        = number
  default     = 7
}

variable "sources" {
  description = "Noms des sources collectees (colonne nom de sources.csv)"
  type        = list(string)
  default     = ["Le Monde", "La Croix", "Le Dauphine Libere", "France 3 Bretagne", "Midi Libre"]
}

# --- Grafana ----------------------------------------------------------------

variable "grafana_image" {
  type    = string
  default = "docker.io/grafana/grafana-oss:12.4.3"
}

variable "grafana_node_port" {
  description = "Port ouvert sur le serveur pour Grafana (plage 30000-32767)"
  type        = number
  default     = 30300
}

variable "grafana_root_url" {
  type    = string
  default = "http://servemilien:30300/"
}
