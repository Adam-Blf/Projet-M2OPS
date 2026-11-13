# Note de cadrage, La gazette

Projet M2Ops, Bloc 3, TD 1. Binôme Adam Beloucif et Emilien Morice.
Rédigée le 13 novembre 2026.

## Le besoin, avec nos mots

Chaque matin, les rédactions françaises publient plusieurs centaines d'articles.
Personne ne peut les lire avant 7 h. **La gazette** produit donc un résumé des
thèmes du jour : quels sujets occupent la presse, sur quels titres, avec un lien
vers la suite. Ce n'est pas un lecteur d'actualité, c'est un **radar éditorial**.

Trois questions auxquelles l'édition de 7 h doit répondre sans qu'on ouvre un
seul site : quels sont les grands sujets du matin, quels titres les traitent, et
où lire la suite.

## Périmètre

### Dedans

- Lecture des flux de **4 titres de PQR** et **5 titres de PQN**, sans jamais
  stocker autre chose qu'un titre, un extrait court, un lien et une date.
- Stockage brut horodaté, nettoyage et contrôles qualité, regroupement des
  articles par thèmes.
- Une édition datée, produite chaque matin avant 7 h, versionnée et rejouable.
- Supervision du pipeline : ce qui est passé, ce qui a échoué, ce qui manque.
- Chaîne CI/CD et infrastructure décrite en code.

### Dehors

- Aucun front soigné : l'édition est un fichier lisible, pas un site.
- Aucun résumé par LLM. Le regroupement par thèmes se fait par similarité
  lexicale, pas par génération de texte.
- Aucun scraping du texte intégral, aucun contournement de paywall.
- Aucune donnée personnelle : pas de commentaires, pas de profils, pas de
  journalisation d'adresses IP de lecteurs.
- Aucune dépense : les machines de l'équipe jusqu'à l'infrastructure fournie en
  TD 4 ou TD 6.

## Contraintes

| Contrainte | Ce que ça impose |
|---|---|
| Édition à 7 h | Le pipeline doit être déclenché la nuit et être prévisible, pas lancé à la main |
| Article de moins de 24 h | Filtrage par date de publication, et gestion des flux qui republient de l'ancien |
| Conditions des éditeurs | Métadonnées seulement, attribution et lien systématiques, débit faible |
| Budget zéro | Tout tourne en local, en conteneurs, sur une seule machine |
| Zéro donnée personnelle | Aucune collecte au-delà des champs de l'article |
| Reproductibilité | Tout ce qui tourne est décrit dans le dépôt, y compris l'ordonnancement |

## La matière, et ce qu'on a le droit d'en faire

La veille de la séance a donné un résultat net, et il oriente l'architecture.
Le RSS reste le canal le plus simple et le plus stable, mais **la presse
quotidienne n'est pas homogène** : sur deux cent trois adresses testées à la main
le 13 novembre 2026, quatre-vingt-cinq rendent un flux XML avec des articles, le
reste refuse les robots, renvoie une page HTML ou n'existe plus.

- ouverts : soixante-quatre flux régionaux et vingt-et-un nationaux, listés dans
  `sources.csv` avec le nombre d'articles vu au test ; y compris les cinq DROM ;
- fermés en 403 : La Voix du Nord, Le Télégramme, Les Échos, Courrier Picard,
  Paris Normandie, Nord Littoral, L'Union, L'Ardennais, Le Journal de l'île de La
  Réunion et 20 Minutes Rouen ;
- renvoient du HTML au lieu d'un flux : La 1ère (toutes éditions), Var-Matin,
  Politis ;
- renvoient un 404 : La Montagne, L'Yonne Républicaine, La République du Centre,
  L'Écho Républicain, Le Berry Républicain, Le Journal du Centre, La Nouvelle
  République, Presse-Océan, Le Maine Libre, Le Courrier de l'Ouest, Le Populaire
  du Centre, La Provence, La Marseillaise, Corse-Matin, Corse Net Infos, Isula,
  France-Antilles, RCI, Le Quotidien de La Réunion, Le Point et Le Parisien aux
  adresses testées.

Quatre enseignements. La PQR du groupe EBRA ouvre ses flux sans difficulté, et les
médias d'enquête locaux ouvrent les leurs, donc le périmètre régional est
atteignable sans contournement. Plusieurs titres demandent le suffixe `.xml`
(`/rss.xml` rend du XML là où `/rss` rend un 404, cas de La Dépêche, Midi Libre,
L'Indépendant, Sud Ouest, Charente Libre et La Croix) : le suffixe fait partie du
contrat d'accès, pas d'un réglage. Les flux régionaux de France 3, stables et à
trente articles, débloquent à eux seuls la Normandie, la Corse et le
Centre-Val de Loire. Le repli par le flux de recherche Google News a été
**testé puis écarté** : une requête par titre ne rend qu'un seul élément, ce qui
ne fait pas une source.

### Couverture et ligne éditoriale

Deux règles de sélection, posées par l'équipe :

1. **Deux sources minimum par région**, avec au moins un titre qui couvre
   réellement la région et non un flux national filtré au mieux. Une région qui
   n'atteint pas le seuil est signalée comme telle plutôt que complétée par une
   source de complaisance.
2. **Aucun média d'extrême droite.** Sont écartés Rivarol, Minute, Présent,
   Valeurs actuelles, Livre Noir, Frontières, France-Soir et équivalents. On privilégie la
   diversité des natures : quotidien régional, édition locale d'un gratuit
   national, média d'enquête local.

Ce que la contrainte produit, honnêtement : les treize régions métropolitaines
atteignent le seuil, avec cinq sources régionales en Bretagne, en
Bourgogne-Franche-Comté, en Grand Est et en Nouvelle-Aquitaine, et sept en
Occitanie. En outre-mer, la Guadeloupe, la Martinique et La Réunion en ont deux ou
trois ; la Guyane n'en a qu'une (Blada, France-Guyane et Mo'News injoignables) et
Mayotte une seule (Mayotte Hebdo, Le Journal de Mayotte et Kwezi injoignables).
Pour combler ces deux-là il faudrait une source payante ou un accès négocié :
deux options hors de portée d'un budget zéro, et le seuil est donc signalé plutôt
que maquillé.

La règle de contenu est la même partout : **titre, extrait court, lien, date**.
Jamais le corps de l'article, jamais de copie qui dispenserait de cliquer.

## Stack retenue, et pourquoi

Le critère de choix n'est pas la modernité, c'est ce qui tient debout sur une
machine, sans budget, et qui se teste.

| Couche | Choix | Pourquoi |
|---|---|---|
| Langage | Python 3.12 | Écosystème data et parsing le plus direct, lisible par les deux membres |
| Collecte | httpx et feedparser | HTTP explicite avec délais et en-têtes maîtrisés, parsing RSS tolérant |
| Stockage brut | Parquet sur volume Docker | Colonnes et compression, relisible sans base, versionnable par date |
| Requêtes | DuckDB | Lecture directe du Parquet, aucun serveur à administrer |
| Qualité | Polars et pytest | Transformations rapides et contrôles exécutables en CI |
| Thèmes | TF-IDF et KMeans (scikit-learn) | Déterministe, réglable, sans modèle à télécharger ni GPU |
| Livraison | Markdown et JSON datés | Lisible par un humain, consommable par la supervision |
| Ordonnancement | cron dans un conteneur dédié | Le plus simple qui garantit l'heure de 7 h |
| CI/CD | GitHub Actions | Gratuit sur dépôt public, déjà lié au dépôt |
| Conteneurs | Docker et Docker Compose | Socle du TD 2, portable vers Kubernetes en TD 4 |
| Supervision | Logs JSON, healthcheck, puis Prometheus et Grafana | Commence sans dépendance, s'étend quand le besoin est prouvé |
| Infrastructure | Terraform et Ansible en TD 6 | Décrire plutôt que cliquer, rejouable et relisible |

## Alternatives écartées, et pourquoi

| Alternative | Écartée parce que |
|---|---|
| Airflow | Un planificateur complet à administrer pour cinq tâches quotidiennes : le coût de panne dépasse le service rendu |
| Kubernetes dès le TD 1 | Trois semaines avant d'avoir un flux qui tourne, et rien à observer encore |
| Scraping HTML du texte intégral | Contraire aux conditions des éditeurs, et le sujet est le thème du jour, pas l'article |
| Résumé par LLM | Hors périmètre annoncé, coût et non-déterminisme, et le pipeline doit rester rejouable à l'identique |
| SQLite seul | Suffisant pour la collecte, faible pour relire des colonnes et rejouer une journée |
| Google News comme source unique | Un seul point de défaillance, et on perdrait la lecture directe des titres qui l'autorisent |
| n8n ou équivalent no-code | Peu testable, peu versionnable, et la grille regarde la CI/CD |

## Risques

| Risque | Effet | Parade retenue |
|---|---|---|
| Un flux change d'adresse ou ferme | Collecte partielle, édition incomplète | Un connecteur par titre, test de vie en CI, rapport de collecte par source |
| Blocage anti-robot | 403 en série | Débit faible, agent identifié, aucune insistance, titre écarté et documenté |
| Volume trop faible avant 7 h | Édition vide | Fenêtre de 24 h glissante et seuil minimal, édition dégradée signalée |
| Doublons entre titres | Thèmes faussés | Déduplication par URL canonique puis par similarité de titre |
| Dérive du regroupement | Thèmes incohérents d'un jour à l'autre | Graine fixe, nombre de thèmes borné, relecture manuelle en début de module |
| Interprétation juridique des extraits | Reproche d'un éditeur | Extraits très courts, attribution et lien systématiques, retrait sur demande |
| Panne silencieuse la nuit | Aucune édition, personne prévenu | Alerte sur absence d'édition, pas seulement sur erreur |

## Rôles

| Qui | Périmètre |
|---|---|
| Adam | Collecte, conteneurisation, CI/CD, infrastructure, supervision |
| Emilien | Qualité des données, stockage, regroupement par thèmes, tests |
| Ensemble | Revue des choix, relecture de l'édition, rapport technique |

Les deux membres installent Docker, Git, Python et un accès au dépôt avant le
TD 2.

## Prochaine étape

TD 2, le socle : dépôt structuré, premiers conteneurs, première chaîne
d'intégration continue. Le schéma de ce qu'on construit est dans
[architecture.md](architecture.md), les sources vérifiées dans
[../sources.csv](../sources.csv).
