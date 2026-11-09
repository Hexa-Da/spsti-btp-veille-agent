#!/usr/bin/env python3
"""2e appel agent cloud : résumé des articles sélectionnés → data/rapport.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DOCTRINE, RAPPORT_PATH, api_key, selected_items
from cursor_agent import run_prompt


def build_prompt(items: list[dict], doctrine: str) -> str:
    # Pas de corps local (Légifrance 403) : l'agent doit ouvrir chaque URL.
    payload = json.dumps({"items": items}, ensure_ascii=False, indent=2)
    return f"""Tu rédiges une revue de veille courte pour une lectrice non technique, sur la médecine du travail (France).

## Doctrine
{doctrine}

## Articles retenus (JSON)
{payload}

## Mission
1. Pour chaque item, **ouvre l'URL** et lis la page (texte officiel / arrêt). L'`extrait` n'est qu'un indice : la synthèse doit venir de la page ouverte, pas de l'extrait seul.
2. Si une URL est inaccessible, indique-le en une phrase dans la synthèse de cet item ; n'invente pas le contenu.
3. Rédige un rapport Markdown en français, strictement sur ce canevas :

```
# Veille médecine du travail — AAAA-MM-JJ

### <titre du 1er article>
<synthèse enrichie>
**Source** : <nom de la source>
**Date** : <date en français>
**Lien** : <URL exacte>

### <titre du 2nd article>
<synthèse enrichie>
**Source** : <nom de la source>
**Date** : <date en français>
**Lien** : <URL exacte>
```

Un bloc `###` + synthèse + Source/Date/Lien par article retenu, dans le même ordre que le JSON.
Ton sobre et factuel. Pas d'emoji. Ne fabrique pas d'URL.
"""


def main() -> None:
    key = api_key()
    items = selected_items()
    doctrine_path = DOCTRINE / "instructions.md"
    doctrine = (
        doctrine_path.read_text(encoding="utf-8")
        if doctrine_path.is_file()
        else "Résumer fidèlement les textes retenus."
    )
    print("Appel agent cloud Cursor (rédaction du résumé)…", flush=True)
    md = run_prompt(key, build_prompt(items, doctrine))
    RAPPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAPPORT_PATH.write_text(md.rstrip() + "\n", encoding="utf-8")
    print(f"Rapport → {RAPPORT_PATH}")


if __name__ == "__main__":
    main()
