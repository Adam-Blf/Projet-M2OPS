# Versions de Terraform et des providers.
# Les versions exactes retenues sont figees dans .terraform.lock.hcl (commite).
terraform {
  required_version = ">= 1.9"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
  }

  # Etat local (terraform/terraform.tfstate) : il contient les mots de passe,
  # il est ignore par git et cree en 600 par bin/tf.
}

provider "kubernetes" {
  config_path = pathexpand(var.kubeconfig_path)
}
