# CI/CD et Sécurisation - Projet M2Ops

## État des lieux actuel

Le projet dispose déjà d'un pipeline GitHub Actions basique mais qui manque de certaines bonnes pratiques de sécurité et de complétude.

### Pipeline existant (.github/workflows/ci.yml)

```yaml
name: CI/CD M2Ops

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest httpx feedparser duckdb psycopg2-binary

      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 src/ --max-line-length=100

      - name: Run tests
        run: |
          python -m pytest tests/ -v

      - name: Build Docker image
        run: |
          docker build -t ghcr.io/Adam-Blf/Projet-M2OPS:${{ github.sha }} -t ghcr.io/Adam-Blf/Projet-M2OPS:latest .

      - name: Push Docker image
        run: |
          echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u Adam-Blf --password-stdin
          docker push ghcr.io/Adam-Blf/Projet-M2OPS:${{ github.sha }}

      - name: Verify tag
        run: |
          echo "Image taggée : ghcr.io/Adam-Blf/Projet-M2OPS:${{ github.sha }}"
```

---

## ✅ Ce qui est Bien

1. **CI trigger** : Push et PR sur `main` uniquement
2. **Python 3.12** : Version récente et supportée
3. **Lint** : Flake8 pour la qualité de code
4. **Tests** : Pytest exécuté
5. **Docker build** : Image multi-étapes pushée sur GHCR
6. **Authentication** : Utilisation de secret GHCR_TOKEN (mieux que dans le code)

### Points forts du projet :
- ✅ `CONTRIBUTING.md` avec conventions de commits (Commits Conventionnels)
- ✅ `CODEOWNERS` implicite via binôme Adam/Emilien
- ✅ `docker-compose.yml` pour le développement local
- ✅ `Dockerfile` multi-étapes (non root)
- ✅ `bin/test` et `bin/dev` pour l'orchestration locale
- ✅ Couverture des sources dans `sources.csv` avec vérification manuelle

---

## ⚠️ Ce qui manque (Sécurité et Complétude)

### 1. **Secret Scan** - Détection des clés API

**Risque** : Le `GHCR_TOKEN` est passed en ligne de commande. Si ce secret est compromis, n'importe qui peut pousser des images sur le registre.

**Ajout recommandé** :
```yaml
- name: Scan for secrets
  run: |
    # Utiliser gitleaks ou secret_scan pour détecter les clés en dur
    pip install gitleaks
    gitleaks detect --staged
```

### 2. **Dependency Review** - Vérification des bibliothèques

**Risque** : `pip install ... httpx feedparser duckdb psycopg2-binary` sans vérification des vulnérabilités.

**Ajout recommandé** :
```yaml
- name: Check dependency vulnerabilities
  run: |
    pip install safety
    safety check --full-report
    # Ou: pip-audit --full-report
```

### 3. **CodeQL / Security Scan** - Analyse statique

**Manquant** : Aucune analyse de sécurité du code Python.

**Ajout recommandé** :
```yaml
- name: CodeQL Initialization
  uses: github/codeql-action/init@v2
  with:
    languages: python

- name: CodeQL Analysis
  uses: github/codeql-action/analyze@v2
```

### 4. **Branche protection** - Verrouillage main

**Bien que** le workflow se déclenche sur `push` vers `main`, il n'y a pas de protection obligatoire sur le dépôt GitHub lui-même. Il faudrait exiger :
- **Pull Request obligatoire** avant tout merge vers `main`
- **Review requirement** (1 approbation minimum)
- **Status check required** (le CI doit passer avant merge)

### 5. **Rollback strategy** - Plan de retour arrière

**Manquant** : En cas de déploiement Docker cassé, pas de procédure de rollback documentée.

**Recommandé** :
- Tagger chaque image (`ghcr.io/Adam-Blf/Projet-M2OPS:${{ github.sha }}` est bon)
- Documenter la commande de rollback : `docker pull ghcr.io/Adam-Blf/Projet-M2OPS:previous-tag`
- Garder au moins 3 versions précédentes en cache

### 5. **Test coverage report** - Rapport de couverture

**Manquant** : Les tests Pytest s'exécutent mais aucun rapport de couverture n'est publié.

**Recommandé** :
```yaml
- name: Check test coverage
  run: |
    pip install coverage
    python -m pytest tests/ --cov=src --cov-report=xml
    pip install codecov
    codecov upload-file coverage.xml
```

### 6. **Lint sur tout le projet** - Lint étendu

**Partiel** : Seule `flake8 src/` est exécutée. Il faudrait aussi checker les tests et la config.

**Recommandé** :
```yaml
- name: Lint all project
  run: |
    pip install flake8
    flake8 . --max-line-length=100 --extend-ignore=E203,W503
```

### 7. **Container security** - Sécurité Docker

**Risque** : L'image Docker n'est pas scannée pour les vulnérabilités.

**Recommandé** :
```yaml
- name: Docker Scan
  run: |
    pip install docker_scan
    docker_scan analyse ghcr.io/Adam-Blf/Projet-M2OPS:latest
```

### 8. **Secrets non en dur** - Vérification supplémentaires

**Observé** : Le `GHCR_TOKEN` est utilisé mais il faudrait s'assurer qu'aucun autre secret (clés API, mots de passe de base de données) n'est en dur dans le code ou les fichiers de config.

**Vérifier que** :
- `.env` fichiers sont dans `.gitignore`
- Aucune clé API dans `src/` ou `docs/`
- Les connexions DB utilisent des variables d'environnement

---

## 🛡️ Checklist Sécurité CI/CD pour M2OPS

Avant de considérer le CI "sécurisé", vérifier ces points :

| # | Élément | Status | Action |
|---|---------|--------|--------|
| 1 | **Secrets en variables d'action** ✅ | GHCR_TOKEN utilisé | Vérifier qu'aucun autre secret n'est en dur |
| 2 | **Secret Scan** ❌ | Non configuré | Ajouter `gitleaks detect` |
| 3 | **Dependency Check** ❌ | Non configuré | Ajouter `safety check` ou `pip-audit` |
| 4 | **CodeQL** ❌ | Non configuré | Initialiser l'analyse CodeQL |
| 5 | **Branche protection** ⚠️ | Partielle | Exiger PR + review sur GitHub |
| 6 | **Test coverage** ⚠️ | Partiel | Publier rapport de couverture |
| 7 | **Docker security scan** ❌ | Non configuré | Ajouter scan d'image |
| 8 | **Rollback plan** ⚠️ | Documenté dans README | Documenter les étapes de rollback |
| 9 | **Licence check** ✅ | LICENSE MIT présente | Maintenir à jour |
| 10 | **Conventional Commits** ✅ | CONTRIBUTING.md présente | Maintenir la règle |

---

## 📋 Pipeline CI/CD Recommandé (Version Complète)

Voici à quoi devrait ressembler le workflow idéal :

```yaml
name: CI/CD M2Ops - Sécurisé

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ---------- 1. SECRET SCAN ----------
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install gitleaks
        run: pip install gitleaks
      - name: Run secret scan
        run: gitleaks detect --staged --verbose

  # ---------- 2. DEPENDENCY CHECK ----------
  dependency-check:
    runs-on: ubuntu-latest
    needs: secret-scan
    steps:
      - uses: actions/checkout@v4
      - name: Install safety
        run: pip install safety
      - name: Check vulnerabilities
        run: safety check --full-report

  # ---------- 3. CODEQL ANALYSIS ----------
  codeql:
    runs-on: ubuntu-latest
    needs: dependency-check
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v2
        with:
          languages: python
      - uses: github/codeql-action/analyze@v2

  # ---------- 4. BUILD & TEST ----------
  build-and-test:
    runs-on: ubuntu-latest
    needs: codeql
    strategy:
      matrix:
        python-version: ["3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest httpx feedparser duckdb psycopg2-binary

      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 . --max-line-length=100

      - name: Run tests
        run: |
          python -m pytest tests/ -v --cov=src --cov-report=xml

      - name: Publish coverage
        run: |
          pip install codecov
          codecov upload-file coverage.xml

  # ---------- 5. DOCKER BUILD & PUSH ----------
  deploy:
    runs-on: ubuntu-latest
    needs: build-and-test
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name. Login to GHCR
        uses: docker/login-action@v3
        with:
          ghcr_token: ${{ secrets.GHCR_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/Adam-Blf/Projet-M2OPS:latest
            ghcr.io/Adam-Blf/Projet-M2OPS:${{ github.sha }}

      - name: Verify image
        run: |
          docker pull ghcr.io/Adam-Blf/Projet-M2OPS:latest
          docker images ghcr.io/Adam-Blf/Projet-M2OPS

  # ---------- 6. SLACK NOTIFICATION ----------
  notify:
    runs-on: ubuntu-latest
    needs: deploy
    if: always()  # S'exécute quel que soit le résultat
    steps:
      - name: Send Slack notification
        uses: slackapi/slack-github-action@v1.27.0
        with:
          channel-id: ${{ secrets.SLACK_CHANNEL_ID }}
          payload: |
            {
              "text": "*CI/CD M2Ops* : ${needs.build-and-test.outcome} → ${needs.deploy.outcome}"
            }
```

---

## 🎯 Priorités d'action pour M2OPS

### Immédiat (à faire cette semaine) :

1. **Ajouter secret scan** : `gitleaks detect --staged` dans le workflow CI
2. **Activer la protection de branche** sur GitHub : Exiger PR + review avant merge vers `main`
3. **Ajouter safety check** : `pip install safety && safety check --full-report`

### Court terme (ce mois-ci) :

4. **Activer CodeQL** : Ajouter l'initialisation et l'analyse CodeQL
5. **Publier coverage** : Intégrer codecov après les tests Pytest
6. **Documenter rollback** : Ajouter une section "Rollback" dans le README

### Moyen terme (semaine prochaine) :

7. **Container security scan** : Intégrer `docker scan` ou `trivy`
8. **Dependency automation** : Activer Dependabot pour les mises à jour de sécurité
9. **Secrets audit** : Auditer tout le code pour s'assurer qu'aucune clé n'est en dur

---

## 📝 Notes spécifiques au projet

### Projet "La Gazette" (M2Ops) :

- **Fréquence** : Déploiement quotidien (chaque matin avant 7h)
- **Stack** : Python → Docker → PostgreSQL + DuckDB + MLflow + FastAPI
- **Conteneurs** : Podman en local, Docker en CI, Kubernetes en production potentielle
- **Données** : 85 flux PQR vérifiés, sources.csv avec conditions d'accès notées
- **Sensibilité** : Données de presse (non sensibles de santé, mais tout de même des données éditoriales)

### Risques spécifiques :

1. **Accès aux flux PQR** : Les 85 flux sont ouverts mais certains refusent robots → pas de risque critique
2. **Base PostgreSQL** : Doit être sécurisée (mot de passe en env var, pas en dur)
3. **MLflow registry** : Les modèles d'entraînement doivent être protégés (qui peut entraîner ?)
4. **Docker images** : Contiennent Python + dépendances → pas de secrets dedans (bon)

---

**Fichier créé** : `CI-CD-SECURITE.md` dans le répertoire du projet M2OPS
**Dernière mise à jour** : Analyse complète du CI/CD existant et recommandations de sécurité