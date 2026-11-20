# Lire `terraform/cronjobs.tf` : la syntaxe HCL pas à pas

Fiche d'apprentissage du projet M2Ops. Le fichier décrit les deux tâches
planifiées du projet : la **collecte** à 7 h et la **purge** à 7 h 30
(heure de Paris).

Le langage s'appelle **HCL** (HashiCorp Configuration Language). Le fichier
fait deux choses :

1. **`locals`** : préparer des valeurs ;
2. **`resource`** : décrire l'objet Kubernetes (un CronJob) à partir de ces
   valeurs, et le créer deux fois.

---

## 1. Les commentaires

```hcl
# Les deux taches planifiees : collecte (7 h) et purge (7 h 30)
deadline = 600 # collecte bloquee -> arretee apres 10 min
```

`#` commente jusqu'à la fin de la ligne. HCL accepte aussi `//` et
`/* ... */`, mais l'usage courant est `#`.

---

## 2. Argument ou bloc

Tout le fichier repose sur deux formes :

```hcl
schedule = "0 7 * * *"     # ARGUMENT : nom = valeur

metadata {                  # BLOC : nom { contenu }
  name = "collector"
}
```

- Un **argument** s'écrit avec `=`. Il reçoit une valeur : chaîne, nombre,
  liste, map, etc.
- Un **bloc** s'écrit sans `=`, avec des accolades. C'est une sous-partie
  structurée qui contient d'autres arguments ou blocs.

C'est le provider Kubernetes qui décide ce qui est un bloc et ce qui est un
argument. Par exemple, `labels = { ... }` est un argument (dont la valeur est
une map), alors que `metadata { ... }` est un bloc. Il n'y a pas de règle à
deviner : c'est écrit dans la documentation du provider.

Un bloc peut être **répété** :

```hcl
volume { name = "data" ... }
volume { name = "tmp"  ... }
```

En YAML, on aurait une liste `volumes: [ ... ]`. En HCL, on écrit le bloc
deux fois.

---

## 3. Le bloc `locals` : les variables internes

```hcl
locals {
  jobs = {
    collector = { ... }
    purge     = { ... }
  }
}
```

`locals` définit des valeurs calculées, que tout le dossier peut lire sous la
forme `local.<nom>`.

> Attention : **`locals`** au pluriel pour les définir, **`local.jobs`** au
> singulier pour les lire.

### Les types de valeurs

| Syntaxe | Type | Exemple |
|---|---|---|
| `"..."` | chaîne | `"256Mi"` |
| `600` | nombre | `deadline = 600` |
| `[ a, b ]` | liste (ordonnée) | `["python", "-m", "src.purge"]` |
| `{ cle = valeur }` | map ou objet | `{ RETENTION_DAYS = "7" }` |
| `{}` | map vide | `env = {}` (collecte) |

`local.jobs` est donc une **map d'objets** :

```
jobs
├── collector → { schedule, args, env = {},                 deadline = 600, memory = "256Mi" }
└── purge     → { schedule, args, env = {RETENTION_DAYS=…}, deadline = 300, memory = "128Mi" }
```

Les deux objets ont **les mêmes clés**. C'est ce qui permet de leur appliquer
un seul et même modèle ensuite.

### `var.` : lire une variable

```hcl
schedule = var.collect_schedule
```

Cette ligne lit la variable déclarée dans `variables.tf`, qui vaut
`"0 7 * * *"` par défaut. On change les heures à un seul endroit.

### La ligne la plus dense : les `args` de la collecte

```hcl
args = concat(["python", "-m", "src.collect"], flatten([for s in var.sources : ["--source", s]]))
```

On la lit **de l'intérieur vers l'extérieur**, avec
`var.sources = ["Le Monde", "La Croix", ...]`.

**a. L'expression `for`**, entre crochets, produit une liste :

```hcl
[for s in var.sources : ["--source", s]]
```

Pour chaque source `s`, elle produit `["--source", s]`. On obtient une liste
de listes :

```
[ ["--source","Le Monde"], ["--source","La Croix"], ... ]
```

**b. `flatten(...)`** enlève un niveau d'imbrication :

```
["--source","Le Monde","--source","La Croix", ...]
```

**c. `concat(a, b)`** colle deux listes bout à bout :

```
["python","-m","src.collect","--source","Le Monde","--source","La Croix", ...]
```

On obtient exactement la commande que lance le conteneur. Si on ajoute une
source dans `variables.tf`, la commande se met à jour toute seule.

### `tostring(...)`

```hcl
env = { RETENTION_DAYS = tostring(var.retention_days) }
```

`var.retention_days` est un **nombre** (7). Or Kubernetes n'accepte que des
**chaînes** dans les variables d'environnement. `tostring` le convertit en
`"7"`.

---

## 4. Le bloc `resource`

```hcl
resource "kubernetes_cron_job_v1" "job" {
```

Un bloc `resource` porte deux **étiquettes** :

1. **`"kubernetes_cron_job_v1"`** est le **type**, fourni par le provider
   kubernetes. Le préfixe `kubernetes_` désigne le provider, et `_v1`
   correspond à l'API `batch/v1` de Kubernetes.
2. **`"job"`** est le **nom local**, choisi librement. Il sert uniquement à
   désigner la ressource dans Terraform. Le vrai nom dans k3s est
   `metadata.name`.

### `for_each` : écrire une fois, créer deux fois

```hcl
for_each = local.jobs
```

Terraform parcourt la map et crée **une instance par clé**. À l'intérieur de
la ressource :

- **`each.key`** vaut `"collector"`, puis `"purge"` ;
- **`each.value`** est l'objet correspondant (`each.value.schedule`,
  `each.value.memory`, etc.).

Dans l'état Terraform, on obtient deux adresses :

```
kubernetes_cron_job_v1.job["collector"]
kubernetes_cron_job_v1.job["purge"]
```

**Pourquoi `for_each` plutôt que `count` ?** `count` numérote les instances
(`[0]`, `[1]`). Si on supprime la première, toutes les suivantes se décalent
et Terraform recrée la seconde. Avec `for_each`, chaque instance garde son
nom.

---

## 5. Du Kubernetes écrit en HCL

La structure suit **exactement** celle d'un CronJob en YAML. Seule
l'écriture change :

| YAML (ancien dossier `k8s/`) | HCL (Terraform) |
|---|---|
| `concurrencyPolicy: Forbid` | `concurrency_policy = "Forbid"` |
| `jobTemplate:` | `job_template { }` |
| `securityContext:` | `security_context { }` |
| `envFrom:` (liste) | `env_from { }` (bloc) |
| `volumes:` avec deux éléments | deux blocs `volume { }` |

Règle générale : le **camelCase** de Kubernetes devient du **snake_case**,
et les listes d'objets deviennent des blocs répétés.

### L'imbrication

```
resource
└── metadata            (nom, namespace, labels du CronJob)
└── spec                (planning du CronJob)
    └── job_template    (modèle du Job créé chaque jour)
        └── metadata {} (vide mais exigé par le provider)
        └── spec        (réglages du Job : essais, délai max)
            └── template           (modèle du Pod)
                └── metadata       (labels du Pod)
                └── spec           (le Pod lui-même)
                    ├── security_context
                    ├── container
                    │   ├── env_from / env / dynamic "env"
                    │   ├── resources
                    │   ├── security_context
                    │   └── volume_mount ×2
                    └── volume ×2
```

On trouve **trois `spec`** :

- celui du **CronJob** dit quand lancer ;
- celui du **Job** dit combien d'essais faire et avec quel délai maximum ;
- celui du **Pod** dit quel conteneur lancer et avec quoi.

`metadata {}` est un bloc vide. Le provider exige sa présence même sans
contenu.

---

## 6. Les références à d'autres ressources

```hcl
name = kubernetes_secret_v1.db.metadata[0].name
```

On la lit morceau par morceau :

- `kubernetes_secret_v1.db` est la ressource Secret de `main.tf`
  (type `.` nom local) ;
- `.metadata` est son bloc metadata ;
- **`[0]`** est obligatoire parce que, pour Terraform, un bloc est
  techniquement une **liste** de blocs. Il faut donc prendre le premier,
  même s'il n'y en a qu'un ;
- `.name` donne la valeur finale, `"m2ops-db"`.

**Pourquoi ne pas écrire `"m2ops-db"` en dur ?** Parce que la référence crée
une **dépendance implicite** : Terraform sait qu'il doit créer le Secret
**avant** les CronJob. Il en va de même pour
`kubernetes_service_v1.db.metadata[0].name`, qui donne `"db"`, le nom d'hôte
de PostgreSQL.

`local.ns` et `local.pod_user` sont définis dans `main.tf` : ils valent
`"m2ops"` et `1000`.

---

## 7. L'interpolation dans une chaîne

```hcl
path = "${var.appdata_dir}/data"
```

`${ ... }` insère une expression **à l'intérieur** d'une chaîne. Ici, le
résultat est `/srv/appdata/m2ops/data`. Quand la valeur entière est une
expression, on écrit simplement `var.x`, sans `"${}"`.

---

## 8. Le bloc `dynamic` : générer des blocs

```hcl
dynamic "env" {
  for_each = each.value.env
  content {
    name  = env.key
    value = env.value
  }
}
```

**Le problème :** `env` est un **bloc**, pas un argument, donc
`env = each.value.env` est impossible. Et le nombre de blocs varie : la
collecte n'en a pas de supplémentaire, la purge en a un
(`RETENTION_DAYS`).

**La solution, `dynamic "env"` :**

- `"env"` est le nom du bloc à générer ;
- `for_each` est la collection à parcourir ;
- `content { }` est le modèle d'un bloc ;
- `env.key` et `env.value` désignent l'élément en cours. L'itérateur porte
  **le nom du bloc**, et non `each`, car `each` est déjà pris par la
  ressource.

Résultat pour la purge :

```hcl
env { name = "POSTGRES_HOST"  value = "db" }   # écrit en dur
env { name = "RETENTION_DAYS" value = "7"  }   # généré par dynamic
```

Pour la collecte, la map est vide : `dynamic` ne génère **aucun** bloc.

---

## 9. Ce qui change entre collecte et purge

Tout ce qui varie passe par `each.` :

| Expression | collector | purge |
|---|---|---|
| `each.key` (nom) | `collector` | `purge` |
| `each.value.schedule` | `0 7 * * *` | `30 7 * * *` |
| `each.value.deadline` | 600 s | 300 s |
| `each.value.args` | `src.collect --source …` | `src.purge` |
| `dynamic "env"` | rien | `RETENTION_DAYS=7` |
| `each.value.memory` | 256Mi | 128Mi |

Tout le reste est commun : l'image, la sécurité, les volumes et le fuseau
horaire. Avec kustomize, ces 60 lignes étaient écrites en double dans deux
fichiers YAML. Il suffisait d'oublier une modification dans l'un des deux
pour qu'ils ne soient plus identiques.

---

## 10. Tester sans rien modifier

```bash
bin/tf console
```

Cette commande ouvre une console interactive. On y tape par exemple :

```
local.jobs["collector"].args
```

La console affiche la liste calculée. On en sort avec `exit`.

---

## Aide-mémoire

| Je vois… | Ça veut dire… |
|---|---|
| `nom = valeur` | argument |
| `nom { }` | bloc |
| `locals { x = … }` / `local.x` | définir / lire une valeur interne |
| `var.x` | variable de `variables.tf` |
| `type.nom.attribut` | référence à une autre ressource (crée une dépendance) |
| `bloc[0]` | premier (et unique) bloc |
| `"${expr}/texte"` | expression dans une chaîne |
| `[for x in liste : …]` | transformer une liste |
| `concat`, `flatten`, `tostring` | fonctions intégrées |
| `for_each` + `each.key` / `each.value` | plusieurs instances d'une ressource |
| `dynamic "bloc" { for_each … content { } }` | générer des blocs répétés |
