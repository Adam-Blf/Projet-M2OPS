# Projet M2Ops, La gazette

Projet certifiant du **Bloc 3** du Mastère Data Engineering & IA de l'EFREI,
promotion 2025-2027, module de 35 heures.

Binôme : **Adam Beloucif** ([Adam-Blf](https://github.com/Adam-Blf)) et
**Emilien Morice** ([emilien754](https://github.com/emilien754)).

## Le projet

**La gazette** produit chaque matin, avant 7 h, une édition qui dit quels sujets
occupent la presse française : les thèmes du jour, les titres qui les traitent,
et où lire la suite. Pas un lecteur d'actualité, un radar éditorial.

Le pipeline cible tient en six boîtes : collecte des flux, stockage brut,
nettoyage et contrôle qualité, regroupement par thèmes, livraison de l'édition,
supervision. Chaque TD en construit une ou deux, la fin du module fait tourner
l'ensemble seul, chaque matin, observé et reproductible.

Cadre posé par le module : édition à 7 h, articles de moins de 24 h, conditions
des éditeurs respectées, aucune donnée personnelle, budget zéro, aucune
génération de résumé par LLM, aucun scraping du texte intégral.

## Livrables du TD 1, cadrage et bornage

| Fichier | Contenu |
|---|---|
| [docs/cadrage.md](docs/cadrage.md) | Besoin reformulé, périmètre, contraintes, stack retenue et alternatives écartées, risques, rôles |
| [docs/architecture.md](docs/architecture.md) | Les six boîtes en Mermaid, ce qui circule entre elles, où ça tourne |
| [sources.csv](sources.csv) | Onze sources vérifiées à la main, PQR et PQN, avec accès et conditions |

## Supports du module

Les supports de cours sont publiés par l'équipe pédagogique sur
[slides.rempart.dev/m2ops-module](https://slides.rempart.dev/m2ops-module/),
sur mot de passe fourni en séance. Une copie locale du deck est gardée dans
`slides/` pour le travail hors ligne. Elle n'est pas publiée ici : ce sont des
documents de cours, pas des livrables de l'équipe.

## Structure

```
docs/           note de cadrage et schéma d'architecture
sources.csv     sources de presse retenues et vérifiées
slides/         copie locale des supports, non publiée (voir .gitignore)
```

Les conteneurs, la collecte et la CI arrivent au TD 2.

## Le module

Mise en situation professionnelle centrée sur l'implémentation, l'automatisation,
la supervision et l'optimisation du déploiement de solutions de données sur le
cloud et on-premise. Le projet mobilise Intégration et Déploiement continu,
MLOps et DataOps, Infrastructure Orchestration et Automation, Sécurité 1 et
Data Engineering on Cloud.

### Compétences évaluées

| Code | Compétence |
|---|---|
| C7.1 | Piloter une stratégie d'intégration continue des pipelines de données, avec conteneurisation et orchestration |
| C7.2 | Développer et automatiser des pipelines CI/CD fiables, testés et conformes |
| C7.3 | Automatiser les traitements et le stockage des données pour améliorer qualité, sécurité, fiabilité et conformité |
| C7.4 | Superviser, versionner et déployer automatiquement les modèles en contexte MLOps |
| C8.1 | Administrer et monitorer les ressources cloud et on-premise pour garantir disponibilité, sécurité, conformité et résilience |
| C8.2 | Automatiser la gestion et le déploiement des infrastructures avec des outils d'Infrastructure as Code |

### Évaluation

Le module porte la **partie 2** de l'évaluation du Bloc 3, soit 25 % de la note
du bloc.

| Partie | Poids dans le Bloc 3 |
|---|---|
| Dossier écrit, partie 1 : certification DP-700 (C6.1 à C6.4) | 15 % |
| Dossier écrit, partie 2 : étude de cas M2Ops (C7.1 à C8.2) | 25 % |
| Passage devant jury, 30 minutes dont 15 de présentation et 15 d'échange | 60 % |

La présentation est collective, la note est individualisée. Le rapport écrit est
d'ordre technique et documente les choix méthodologiques, les outils utilisés et
les résultats obtenus.

### Déroulé

| Étape | Contenu |
|---|---|
| 1. Cadrage | Contexte, objectifs, ressources, contraintes, périmètre CI/CD, DataOps, MLOps et infrastructure |
| 2. Stratégie CI/CD | Gestion de versions, tests, étapes build, test, validation et livraison |
| 3. Automatisation des traitements | Flux reproductibles, erreurs et reprises, alertes, dépendances, conformité |
| 4. MLOps | Versionnement des modèles et artefacts, évaluation, déploiement automatisé |
| 5. Monitoring | Indicateurs de performance, sécurité, disponibilité et conformité, résilience |
| 6. Infrastructure as Code | Configuration versionnée, déploiement automatisé, cohérence entre environnements |
| 7. Consolidation | Cohérence de bout en bout, risques, limites, recommandations, rapport technique |

## Outils de référence

GitHub Actions, GitLab CI/CD, Docker, Kubernetes, Terraform, Ansible, MLflow,
Airflow, Prometheus, Grafana. Conformité traitée avec le guide RGPD de la CNIL.

## Licence

MIT, voir [LICENSE](LICENSE).
