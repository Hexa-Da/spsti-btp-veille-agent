#!/usr/bin/env python3
"""2e appel agent cloud : résumé des retenus → data/rapport.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DOCTRINE, RAPPORT_PATH, RETENUS_PATH, api_key, read_json
from cursor_agent import run_prompt


def build_prompt(retenus: dict, doctrine: str) -> str:
    # Corps déjà limités par enrich.py ; on envoie le JSON des retenus
    payload = json.dumps(retenus, ensure_ascii=False, indent=2)
    return f"""Tu rédiges une revue de veille courte pour une lectrice non technique, sur la médecine du travail (France).

## Doctrine
{doctrine}

## Articles retenus (JSON)
{payload}

## Mission
Rédige un rapport Markdown en français, strictement sur ce canevas :

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
    retenus = read_json(RETENUS_PATH)
    if not retenus or not retenus.get("items"):
        raise SystemExit(f"Aucun retenu : lancez enrich.py ({RETENUS_PATH})")
    doctrine_path = DOCTRINE / "instructions.md"
    doctrine = (
        doctrine_path.read_text(encoding="utf-8")
        if doctrine_path.is_file()
        else "Résumer fidèlement les textes retenus."
    )
    print("Appel agent cloud Cursor (rédaction du résumé)…", flush=True)
    md = run_prompt(key, build_prompt(retenus, doctrine))
    RAPPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAPPORT_PATH.write_text(md.rstrip() + "\n", encoding="utf-8")
    print(f"Rapport → {RAPPORT_PATH}")


if __name__ == "__main__":
    main()
