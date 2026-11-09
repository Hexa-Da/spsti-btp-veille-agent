#!/usr/bin/env python3
"""2e appel agent cloud : résumé des articles sélectionnés → data/rapport.md."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import RAPPORT_PATH, api_key, selected_items
from cursor_agent import run_prompt

_TITLE = re.compile(r"^#\s*Veille médecine du travail\b", re.M)


def build_prompt(items: list[dict]) -> str:
    # Pas de corps local (Légifrance 403) : l'agent doit ouvrir chaque URL.
    payload = json.dumps({"items": items}, ensure_ascii=False, indent=2)
    return f"""Tu rédiges une revue de veille courte pour une lectrice non technique, sur la médecine du travail (France).

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
Réponds uniquement avec le Markdown du rapport (pas de préambule, pas de conclusion). N'écris aucun fichier.
"""


def extract_rapport_md(text: str) -> str:
    """Garde le corps Markdown ; refuse un chat méta (fichier écrit ailleurs, etc.)."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not _TITLE.search(text):
        raise SystemExit(
            "Réponse agent hors canevas (attendu un titre « # Veille médecine du travail »). "
            "Rien n'a été écrit dans rapport.md."
        )
    return text


def main() -> None:
    key = api_key()
    items = selected_items()
    print("Appel agent cloud Cursor (rédaction du résumé)…", flush=True)
    md = extract_rapport_md(run_prompt(key, build_prompt(items)))
    RAPPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAPPORT_PATH.write_text(md.rstrip() + "\n", encoding="utf-8")
    print(f"Rapport → {RAPPORT_PATH}")


if __name__ == "__main__":
    # self-check hors API
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        ok = extract_rapport_md(
            "```markdown\n# Veille médecine du travail — 2026-11-09\n\n### Titre\ntexte\n```"
        )
        assert ok.startswith("# Veille"), ok
        try:
            extract_rapport_md("J'ai rédigé la revue… enregistré dans x.md")
        except SystemExit:
            pass
        else:
            raise SystemExit("self-check: méta-chat aurait dû être rejeté")
        print("self-check ok")
        raise SystemExit(0)
    main()
