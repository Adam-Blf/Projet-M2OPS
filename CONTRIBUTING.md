# Contributing au projet M2Ops

## Règles de contribution

### Nommage des branches

- Une branche par sujet/new feature
- La branche doit porter un nom descriptif, ex: `feat/collecte-flux`, `fix/bug-test`
- Pour les corrections de bugs : `fix/nom-du-bug`

### Format des commits

On utilise les **Conventional Commits** :

```
<type>: <description>

[optionnel: corps du commit]

[optionnel: footer]
```

Types autorisés :
- `feat` : nouvelle fonctionnalité
- `fix` : correction de bug
- `docs` : modification de documentation
- `style` : formatage, ponctuation, absence d'impact sur le code
- `refactor` : refactoring qui ne corrige pas de bug ni n'ajoute de fonctionnalité
- `test` : ajout de tests manquants ou correction de tests existants
- `chore` : tâches de maintenance (dependencies, configuration, etc.)

Exemples :
- `feat: ajouter le parseur de flux RSS`
- `fix: corriger l'index unique sur url_canonique`
- `docs: mise à jour du README avec les instructions TD 2`

### Pull Request

1. Ouvrir une PR depuis la branche sujet vers `main`
2. La PR doit inclure une description claire des changements
3. Au moins une revue est requise avant merge
4. La CI doit passer (lint + tests) avant merge
5. En cas d'échec CI, le merge est bloqué jusqu'à résolution

### Convention de merge

- Utiliser "Squash and merge" pour garder un historique propre
- Ne jamais merger sur `main` directement sans passer par une PR
- Après merge, supprimer la branche sujet

### Nouveaux contributeurs

- Cloner le dépôt
- Lancer `bin/dev` pour vérifier que l'environnement de dev fonctionne
- Lancer `bin/test` pour vérifier que les tests passent
- Vérifier que le README est à jour avec les nouvelles instructions

## Liens utiles

- [Issues](https://github.com/Adam-Blf/Projet-M2OPS/issues)
- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)
- [CI/CD](.github/workflows/ci.yml)