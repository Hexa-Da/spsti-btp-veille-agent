# Veille médecine du travail (Windows)

Agent cloud Cursor pour collecte et trie des articles, puis rédaction de rapport Word.

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

Les sources pour la collecte sont à mettre dans `sources.json` à la racine du projet

## Usage (double-clic)

1. `01-collecter.bat` — collecte + tri (1er appel)
2. `02-selection.bat` — cochez les articles à garder dans l'UI puis Enregistrer
3. `03-rapport.bat` — résume les articles séléectionné (2nd appel)
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
sources.json     liste des sources
doctrine/        consignes de collecte
scripts/         collect, serve, rapport, export
web/             page de sélection
data/            candidats, sélection, rapport, exports/
```
