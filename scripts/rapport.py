#!/usr/bin/env python3
"""2e appel agent cloud : résumé des articles sélectionnés → data/rapport.md."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import RAPPORT_PATH, api_key, selected_items, veille_title
from cursor_agent import run_prompt

_TITLE = re.compile(r"^#\s*Veille juridique du\b.*$", re.M)


def build_prompt(items: list[dict]) -> str:
    # Pas de corps local (Légifrance 403) : l'agent doit ouvrir chaque URL.
    payload = json.dumps({"items": items}, ensure_ascii=False, indent=2)
    title = veille_title()
    return f"""Tu rédiges une veille juridique courte (médecine du travail / droit social, France).

## Articles retenus (JSON)
{payload}

## Mission
1. Pour chaque item, **ouvre l'URL** et lis la page. L'`extrait` n'est qu'un indice : la synthèse doit venir de la page ouverte.
2. Si une URL est inaccessible, indique-le en une phrase dans la synthèse ; n'invente pas le contenu.
3. Rédige un rapport Markdown en français, strictement sur ce canevas :

```
# {title}

### <titre du 1er article>
<synthèse courte, factuelle ; listes « - » si besoin>
<référence seule : ex. Cass. soc., 14 janv. 2026, n°24-19.544  OU  D. n°… : JO, …  OU  URL exacte>

### <titre du 2nd article>
…
```

Règles :
- La première ligne doit être exactement `# {title}` (date du jour fournie ; ne calcule pas de période à partir des articles).
- Pas de rubriques (`## CONTRAT DE TRAVAIL`, etc.) : uniquement des blocs `###` dans l'ordre du JSON.
- Pas de champs Source / Date / Lien : la référence (citation ou URL) suffit, en dernière ligne de l'item.
- Ton sobre. Pas d'emoji. Ne fabrique pas d'URL.
- Réponds uniquement avec le Markdown (pas de préambule, pas de conclusion). N'écris aucun fichier.
"""


def extract_rapport_md(text: str) -> str:
    """Garde le corps Markdown ; impose le titre à la date du jour."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not _TITLE.search(text) and not re.search(r"^###\s+", text, re.M):
        raise SystemExit(
            "Réponse agent hors canevas (attendu un titre « # Veille juridique du … » "
            "ou des blocs ###). Rien n'a été écrit dans rapport.md."
        )
    title_line = f"# {veille_title()}"
    if _TITLE.search(text):
        text = _TITLE.sub(title_line, text, count=1)
    else:
        text = title_line + "\n\n" + text
    return text


def main() -> None:
    key = api_key()
    items = selected_items()
    print("Appel agent cloud Cursor (rédaction du résumé)…", flush=True)
    md = extract_rapport_md(run_prompt(key, build_prompt(items)))
    parent = os.path.dirname(RAPPORT_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(RAPPORT_PATH, "w", encoding="utf-8") as f:
        f.write(md.rstrip() + "\n")
    print(f"Rapport → {RAPPORT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        today = veille_title()
        ok = extract_rapport_md(
            "```markdown\n# Veille juridique du 1 au 7 novembre 2026\n\n"
            "### Titre\ntexte\nCass. soc., 1 nov. 2026, n°1\n```"
        )
        assert ok.startswith(f"# {today}"), ok
        try:
            extract_rapport_md("J'ai rédigé la revue… enregistré dans x.md")
        except SystemExit:
            pass
        else:
            raise SystemExit("self-check: méta-chat aurait dû être rejeté")
        print("self-check ok")
        raise SystemExit(0)
    main()
