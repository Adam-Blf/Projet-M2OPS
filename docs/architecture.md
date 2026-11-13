# Architecture cible

Projet M2Ops, TD 1. Ce schéma fixe les six boîtes du pipeline et la branche
modèle du TD 6, plus ce qui circule entre elles. Chaque TD en construit une ou
deux.

```mermaid
flowchart LR
  S1["1. Collecte des flux<br/>un connecteur RSS par titre"]
  S2["2. Stockage brut<br/>PostgreSQL, tables `articles_brutes` (JSONB)"
  S3["3. Nettoyage et contrôle qualité<br/>contrôles DuckDB, champs requis"]
  S4["4. Regroupement par thèmes (automatique)"]
  M1["Registre de modèles<br/>MLflow, versions et métriques"]
  M2["Service du modèle<br/>FastAPI, version épinglée"]
  S5["5. Livraison de l'édition<br/>Markdown et JSON datés, 7 h"]
  S6["6. Supervision<br/>Prometheus, Loki, alertes"]

  S1 -->|articles bruts| S2
  S2 -->|export Parquet du jour| S3
  S3 -->|articles propres| S4
  S4 -->|modèle entraîné et métriques| M1
  M1 -->|version retenue| M2
  M1 -->|version retenue| S5
  S4 -->|thèmes et volumes| S5
  M2 -.->|étiquette à la demande| S6
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
  class S2,M1 store
  class S3,S4 process
  class S5,M2 ok
  class S6 error
```

## Ce qui circule

| De | Vers | Charge | Volume attendu |
|---|---|---|---|
| Collecte | PostgreSQL, `articles_brutes` | Un document par article : titre, extrait, lien, date, titre de presse, rubrique | Quelques centaines à quelques milliers de documents par jour |
| PostgreSQL, `articles_propres` | Qualité | Export Parquet du jour, relu par DuckDB | Un fichier par jour et par source |
| Qualité | Thèmes | Articles retenus, texte normalisé pour la similarité | Deux tiers du brut environ, doublons et anciens retirés |
| Thèmes | Registre | Matrice TF‑IDF, KMeans (choix k par élbo sur silhouette), hyperparamètres, métriques de cohésion | Un run par entraînement, quelques dizaines par semaine |
| Registre | Livraison | Version du modèle qui a produit l'édition, ses métriques | Une version par jour |
| Registre | Service | Artefact sérialisé et version épinglée | Une image immuable par version |
| Thèmes | Livraison | Thèmes, articles rattachés, compteurs par titre de presse | Une dizaine de thèmes par jour |
| Toutes | Supervision | Compteurs, durées, erreurs par source, logs structurés | Un enregistrement par étape et par exécution |

DuckDB ne lit pas PostgreSQL directement : l'export en Parquet est une étape du
pipeline, assumée et décrite, pas un contournement. Elle sert deux fois, pour les
contrôles qualité et pour les agrégats qui nourrissent l'édition.

## Où ça tourne

| Brique | Où | Quand |
|---|---|---|
| Collecte, qualité, thèmes, livraison | Conteneurs Podman sur une machine de l'équipe, ordonnancés par un CronJob Kubernetes local (kind ou minikube) | Chaque nuit, CronJob à 2 h, édition prête avant 7 h |
| PostgreSQL | Conteneur Podman, volume persistant | En continu |
| MLflow, suivi et registre | Conteneur Podman, backend fichier sur volume, base de suivi sauvegardée | À chaque entraînement |
| Service du modèle | Deployment Kubernetes, image épinglée sur la version du jour | En continu, redémarré à chaque nouvelle version |
| Export et éditions | Volume persistant, un dossier par jour | À chaque exécution |
| Chaîne d'intégration continue | GitHub Actions, images poussées sur GHCR | À chaque poussée et à chaque demande de fusion |
| Supervision | Prometheus, Grafana, Loki et Alertmanager en conteneurs | En continu, alerte si l'édition de 7 h manque |
| Infrastructure décrite | Terraform pour les ressources, Ansible pour la machine, consolidés au TD 9 | À la mise en production |

Les manifestes Kubernetes vivent dans le dépôt, produits depuis les conteneurs
Podman par `podman generate kube`, puis complétés pour le CronJob, les volumes et
le Deployment du modèle. Rien n'est lancé à la main le matin : ce qui décrit
l'heure de 7 h est versionné.

## Ce que chaque TD ajoute

Dix séances, et chaque brique de ce schéma arrive dans l'une d'elles. Le
livrable d'une séance est commité avant la suivante.

| TD | Livrable attendu | Boîtes couvertes | Compétences |
|---|---|---|---|
| TD 1 | La note de cadrage, ce schéma et `sources.csv` dans le dépôt | Cadrage | C7.1 |
| TD 2 | Un push déclenche une CI verte (lint, tests, build) qui publie une image, et le README lance le projet en deux commandes | Socle | C7.1, C7.2, C8.2 |
| TD 3 | La collecte planifiée tourne seule et remplit `articles_bruts`, la table des sources dit l'état de chacune | Collecte, stockage | C7.1, C7.3 |
| TD 4 | Les règles d'exclusion documentées et testées, `articles_propres` alimentée, le rapport de qualité produit à chaque passage | Qualité | C7.3 |
| TD 5 | Un script de regroupement reproductible, chaque run tracé (données, paramètres, métriques, artefacts), les thèmes du jour en base | Thèmes, registre | C7.4 |
| TD 6 | L'évaluation automatique avec seuils dans le pipeline, un registre de versions, un retour arrière testé, la fiche modèle | Registre, service | C7.2, C7.4 |
| TD 7 | Chaque matin à 7 h, l'édition du jour publiée sans geste humain, avec ses contrôles en sortie et son archive, journal de bord ouvert | Livraison | C7.1, C7.2, C7.3 |
| TD 8 | Un tableau de bord (la gazette, la machine, le modèle), deux alertes au moins, un runbook d'incident, une sauvegarde restaurée | Supervision | C8.1 |
| TD 9 | Toute l'infrastructure décrite en code versionné, les secrets hors du dépôt, une reconstruction de zéro démontrée et chronométrée | Infrastructure | C8.1, C8.2 |
| TD 10 | Le rapport technique remis 48 h avant, la démo de bout en bout, la soutenance | Toutes | Toutes |
| Fin de module | Le pipeline tourne seul chaque matin, observé, reproductible et reconstruisable de zéro | | |

## Décisions structurantes

1. **Un connecteur par titre de presse**, pas un collecteur générique : un flux
   qui casse ne doit emporter que sa source.
2. **Le brut n'est jamais modifié.** PostgreSQL garde le document tel que publié
   dans `articles_bruts`, et le nettoyage écrit dans `articles_propres`, une
   collection distincte : une édition passée reste rejouable à l'identique, et
   une règle d'exclusion se rejoue sur l'historique sans rien recollecter.
3. **La déduplication est tenue par la base**, par un index unique sur l'URL
   canonique, pas par une comparaison en mémoire qui dépendrait de l'ordre
   d'arrivée.
4. **L'analyse passe par DuckDB**, sur un export Parquet daté : les contrôles
   qualité et les agrégats se réécrivent en SQL, sans serveur à administrer.
5. **Le modèle est un artefact versionné, pas un fichier local.** Chaque
   entraînement entre dans MLflow avec ses hyperparamètres et ses métriques, et
   l'édition cite la version qui l'a produite. Sans ça, deux éditions ne sont pas
   comparables et rien n'est reproductible.
6. **Une seule version sert l'édition et le service.** L'image du service est
   épinglée sur la version retenue, jamais sur `latest` : ce que l'API répond le
   matin est exactement ce que l'édition a publié.
7. **Podman plutôt que Docker**, pour construire et exécuter sans démon root, et
   parce que la conversion en manifestes Kubernetes est directe.
8. **L'ordonnancement est décrit dans le dépôt**, sous forme de CronJob : c'est
   ce qui rend l'heure de 7 h vérifiable.
9. **La supervision observe l'absence**, pas seulement l'erreur : un pipeline qui
   ne tourne pas ne produit aucun log d'erreur, donc l'alerte porte sur la
   métrique « édition du jour absente ».
