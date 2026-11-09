# Veille médecine du travail (Windows)

Agent cloud Cursor pour collecte et tri des articles, puis rédaction de rapport Word.

## Install

1. Dans PowerShell :

```powershell
winget install -e --id Python.Python.3.12
```

Puis fermer/rouvrir le terminal (pour le PATH). Vérifier : `python --version`.

2. Crée `.env` et coller votre clé :

```
CURSOR_API_KEY=crsr_...
```

Les sources pour la collecte sont à mettre dans `sources.json` à la racine du projet.

## Usage

Double-clic sur `lancer.bat` : l’application s’ouvre dans le navigateur.

1. **Collecter** — 1er appel agent
2. **Cocher** les articles à garder
3. **Générer le Word** — 2e appel agent

## Ajouter une source

Éditez `sources.json`, ajoutez une entrée :

```json
{
  "id": "ma-source",
  "label": "Mon flux",
  "type": "rss",
  "url": "https://exemple.org/flux.xml"
}
```

## Structure

```text
lancer.bat       ouvre l'UI
sources.json     liste des sources
doctrine/        consignes de collecte
scripts/         collect, serve, rapport, export
web/             interface
data/            candidats, sélection, rapport, exports/
```
