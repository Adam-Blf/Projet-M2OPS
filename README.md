<!-- adam-badges:start -->
[![commits](https://img.shields.io/github/commit-activity/t/Adam-Blf/Projet-M2OPS?color=001329&label=commits&style=flat-square)](https://github.com/Adam-Blf/Projet-M2OPS/commits)
[![visites](https://hits.sh/github.com/Adam-Blf/Projet-M2OPS.svg?style=flat-square&label=visites&color=001329)](https://hits.sh/github.com/Adam-Blf/Projet-M2OPS/)
[![last commit](https://img.shields.io/github/last-commit/Adam-Blf/Projet-M2OPS?color=D4A437&style=flat-square&label=dernier%20push)](https://github.com/Adam-Blf/Projet-M2OPS/commits)
[![top language](https://img.shields.io/github/languages/top/Adam-Blf/Projet-M2OPS?style=flat-square)](https://github.com/Adam-Blf/Projet-M2OPS)
[![license](https://img.shields.io/github/license/Adam-Blf/Projet-M2OPS?style=flat-square&color=D4A437)](LICENSE)
<!-- adam-badges:end -->

# Projet M2Ops, La gazette

Projet certifiant du Bloc 3 du Mastère Data Engineering & IA de l'EFREI,
promotion 2025-2027.

Binôme : **Adam Beloucif** ([Adam-Blf](https://github.com/Adam-Blf)) et
**Emilien Morice** ([emilien754](https://github.com/emilien754)).

## Le projet

**La gazette** produit chaque matin, avant 7 h, une édition qui dit quels sujets
occupent la presse française : les thèmes du jour, les titres qui les traitent,
et où lire la suite. Pas un lecteur d'actualité, un radar éditorial.

Cadre du projet : édition à 7 h, articles de moins de 24 h, conditions des
éditeurs respectées, aucune donnée personnelle, budget zéro, aucun résumé généré
par un LLM, aucun scraping du texte intégral. On ne conserve qu'un titre, un
extrait, un lien et une date.

## Architecture

Le pipeline tient en six boîtes. Chaque TD en construit une ou deux, la fin du
module fait tourner l'ensemble seul, chaque matin.

```mermaid
flowchart LR
  S1["Collecte des flux<br/>un connecteur par titre"]
  S2["Stockage brut<br/>Parquet horodaté"]
  S3["Nettoyage et qualité<br/>déduplication, fraîcheur"]
  S4["Regroupement par thèmes<br/>TF-IDF puis KMeans"]
  S5["Livraison de l'édition<br/>Markdown et JSON, 7 h"]
  S6["Supervision<br/>logs, métriques, alerte"]

  S1 -->|articles bruts| S2
  S2 -->|lots du jour| S3
  S3 -->|articles propres| S4
  S4 -->|thèmes et volumes| S5
  S3 -.->|rapport de qualité| S6
  S4 -.->|métriques| S6
  S5 -.->|statut| S6
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

Le détail des flux, des volumes et de l'hébergement de chaque brique est dans
[docs/architecture.md](docs/architecture.md).

## Livrables du TD 1, cadrage et bornage

| Fichier | Contenu |
|---|---|
| [docs/cadrage.md](docs/cadrage.md) | Besoin reformulé, périmètre, contraintes, stack retenue et alternatives écartées, risques, rôles |
| [docs/architecture.md](docs/architecture.md) | Les six boîtes, ce qui circule entre elles, où ça tourne |
| [sources.csv](sources.csv) | 85 flux vérifiés à la main, 64 PQR et 21 PQN, avec accès, conditions et fréquence mesurée |

## Couverture des sources

Le fichier [sources.csv](sources.csv) tient en six colonnes : nom, type, region,
acces, conditions, notes. Chaque adresse a été ouverte à la main avec un agent
identifié, seuls les flux qui rendent du XML avec des articles sont retenus, et
la note dit ce qu'on a le droit d'en faire, la date du test et le rythme de
publication observé.

| Périmètre | Flux |
|---|---|
| Régions métropolitaines (13) | 64 PQR, deux au minimum par région |
| Outre-mer (5 DROM) | 9 flux, 2 en Guadeloupe et en Martinique, 3 à La Réunion, 1 en Guyane et à Mayotte |
| National | 21 PQN |

Sur 203 adresses testées, 85 rendent un flux exploitable. Les autres refusent les
robots, renvoient du HTML au lieu de XML, ou n'existent plus. Les limites
assumées sont écrites dans la note de cadrage plutôt que masquées : Guyane et
Mayotte restent à une seule source, et aucun média d'extrême droite n'est retenu
malgré un flux parfois valide. Le détail des listes écartées est dans
[docs/cadrage.md](docs/cadrage.md).

## Structure

```
docs/           note de cadrage et schéma d'architecture
sources.csv     sources de presse retenues et vérifiées
```

Les conteneurs, la collecte et la chaîne d'intégration continue arrivent au TD 2.

## Licence

MIT, voir [LICENSE](LICENSE).
