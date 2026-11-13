# Architecture cible

Projet M2Ops, TD 1. Ce schéma fixe les six boîtes du pipeline et ce qui circule
entre elles. Chaque TD en construit une ou deux.

```mermaid
flowchart LR
  S1["1. Collecte des flux<br/>un connecteur RSS par titre"]
  S2["2. Stockage brut<br/>MongoDB, documents horodatés"]
  S3["3. Nettoyage et contrôle qualité<br/>contrôles DuckDB, champs requis"]
  S4["4. Regroupement par thèmes<br/>TF-IDF puis KMeans"]
  S5["5. Livraison de l'édition<br/>Markdown et JSON datés, 7 h"]
  S6["6. Supervision<br/>logs JSON, métriques, alerte"]

  S1 -->|articles bruts| S2
  S2 -->|export Parquet du jour| S3
  S3 -->|articles propres| S4
  S4 -->|thèmes et volumes| S5
  S3 -.->|rapport de qualité| S6
  S4 -.->|métriques de regroupement| S6
  S5 -.->|statut de publication| S6
  S6 -.->|relance ou alerte| S1

  classDef input fill:#2563eb,stroke:#1e3a8a,color:#fff
  classDef process fill:#7c3aed,stroke:#4c1d95,color:#fff
  classDef store fill:#f59e0b,stroke:#92400e,color:#111
  classDef ok fill:#16a34a,stroke:#14532d,color:#fff
  classDef error fill:#dc2626,stroke:#7f1d1d,color:#fff

  class S1 input
  class S2 store
  class S3,S4 process
  class S5 ok
  class S6 error
```

## Ce qui circule

| De | Vers | Charge | Volume attendu |
|---|---|---|---|
| Collecte | MongoDB | Un document par article : titre, extrait, lien, date, titre de presse, rubrique | Quelques centaines à quelques milliers de documents par jour |
| MongoDB | Qualité | Export Parquet du jour, relu par DuckDB | Un fichier par jour et par source |
| Qualité | Thèmes | Articles retenus, texte normalisé pour la similarité | Deux tiers du brut environ, doublons et anciens retirés |
| Thèmes | Livraison | Thèmes, articles rattachés, compteurs par titre de presse | Une dizaine de thèmes par jour |
| Toutes | Supervision | Compteurs, durées, erreurs par source | Un enregistrement par étape et par exécution |

DuckDB ne lit pas MongoDB directement : l'export en Parquet est une étape du
pipeline, assumée et décrite, pas un contournement. Elle sert deux fois, pour les
contrôles qualité et pour les agrégats qui nourrissent l'édition.

## Où ça tourne

| Brique | Où | Quand |
|---|---|---|
| Collecte, qualité, thèmes, livraison | Conteneurs Podman sur une machine de l'équipe, ordonnancés par un CronJob Kubernetes local (kind ou minikube) | Chaque nuit, CronJob à 2 h, édition prête avant 7 h |
| MongoDB | Conteneur Podman, volume persistant | En continu |
| Export et éditions | Volume persistant, un dossier par jour | À chaque exécution |
| Chaîne d'intégration continue | GitHub Actions | À chaque poussée et à chaque demande de fusion |
| Supervision | Logs JSON, puis Prometheus et Grafana en conteneurs | En continu |
| Infrastructure décrite | Terraform et Ansible, cible fournie en TD 4 ou TD 6 | À la mise en production |

Les manifestes Kubernetes vivent dans le dépôt, produits depuis les conteneurs
Podman par `podman generate kube`, puis complétés pour le CronJob et les volumes.
Rien n'est lancé à la main le matin : ce qui décrit l'heure de 7 h est versionné.

## Ce que chaque TD ajoute

| TD | Boîtes couvertes |
|---|---|
| TD 2 | Dépôt, conteneurs Podman, premiers manifestes, première CI, aucun flux encore |
| TD 3 | Collecte des flux et stockage MongoDB |
| TD 4 | Nettoyage, contrôles DuckDB et première livraison |
| TD 5 | Regroupement par thèmes et supervision |
| TD 6 | Infrastructure décrite en code, déploiement automatisé |
| Fin de module | Les six boîtes tournent seules, chaque matin, observées et reproductibles |

## Décisions structurantes

1. **Un connecteur par titre de presse**, pas un collecteur générique : un flux
   qui casse ne doit emporter que sa source.
2. **Le brut n'est jamais modifié.** MongoDB conserve le document tel que publié,
   et le nettoyage produit une collection distincte : une édition passée reste
   rejouable à l'identique.
3. **La déduplication est tenue par la base**, par un index unique sur l'URL
   canonique, pas par une comparaison en mémoire qui dépendrait de l'ordre
   d'arrivée.
4. **L'analyse passe par DuckDB**, sur un export Parquet daté : les contrôles
   qualité et les agrégats se réécrivent en SQL, sans serveur à administrer.
5. **Podman plutôt que Docker**, pour construire et exécuter sans démon root, et
   parce que la conversion en manifestes Kubernetes est directe.
6. **L'ordonnancement est décrit dans le dépôt**, sous forme de CronJob : c'est
   ce qui rend l'heure de 7 h vérifiable.
7. **La supervision observe l'absence**, pas seulement l'erreur : un pipeline qui
   ne tourne pas ne produit aucun log d'erreur.
