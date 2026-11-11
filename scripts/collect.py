#!/usr/bin/env python3
"""Collecte + tri via agent cloud Cursor → data/candidats.json (titre + extrait seulement)."""

import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import CANDIDATS_PATH, INSTRUCTIONS_PATH, api_key, load_sources, write_json
from cursor_agent import extract_json_block, run_prompt

WINDOW_DAYS = 15


def parse_iso_date(value: str) -> date | None:
    raw = (value or "").strip()
    if len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def in_window(value: str, since: date, today: date) -> bool:
    d = parse_iso_date(value)
    return d is not None and since <= d <= today


def build_prompt(sources: dict, doctrine_text: str, since: date, today: date) -> str:
    sources_json = __import__("json").dumps(sources, ensure_ascii=False, indent=2)
    return f"""Tu es un agent de veille sur la médecine du travail et le droit associé (France).

## Doctrine
{doctrine_text}

## Fenêtre (STRICT)
Aujourd'hui : {today.isoformat()}
Ne retiens que les items datés du {since.isoformat()} au {today.isoformat()} inclus (publication ou décision).
Hors fenêtre ou sans date `AAAA-MM-JJ` → écarte.

## Sources à consulter
{sources_json}

## Mission
1. Consulte ces sources (flux RSS type legifrss, pages de recherche Judilibre / Cour de cassation).
2. Retiens uniquement les nouveautés pertinentes dans la fenêtre (médecine du travail, inaptitude, suivi de santé au travail, obligations employeurs / SPSTI liées).
3. Écarte le promotionnel, les nominations sans lien, les sujets hors périmètre, et tout ce qui est plus vieux que {since.isoformat()}.

## Format de sortie (STRICT)
Réponds UNIQUEMENT avec un JSON valide, sans markdown autour, de la forme :
{{
  "items": [
    {{
      "id": "slug-court-unique",
      "titre": "...",
      "url": "https://...",
      "date": "AAAA-MM-JJ",
      "source": "id de la source (ex. legifrance-travail)",
      "extrait": "2 à 4 phrases max, pas le texte intégral"
    }}
  ]
}}

Interdictions : pas de champ "corps", pas de texte intégral d'article, pas de prose hors JSON.
Si aucune nouveauté pertinente : {{"items": []}}.
"""


def main() -> None:
    key = api_key()
    sources = load_sources()
    if os.path.isfile(INSTRUCTIONS_PATH):
        with open(INSTRUCTIONS_PATH, encoding="utf-8") as f:
            doctrine = f.read()
    else:
        doctrine = "Retenir ce qui touche la médecine du travail / inaptitude."

    today = datetime.now(timezone.utc).date()
    since = today - timedelta(days=WINDOW_DAYS)

    print("Appel agent cloud Cursor (collecte + tri)…", flush=True)
    raw = run_prompt(key, build_prompt(sources, doctrine, since, today))
    parsed = extract_json_block(raw)
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        items = parsed.get("items") or []
    else:
        raise SystemExit(f"JSON inattendu : {type(parsed)}")

    cleaned = []
    dropped = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        row = {
            "id": str(it.get("id") or "").strip() or None,
            "titre": str(it.get("titre") or "").strip(),
            "url": str(it.get("url") or "").strip(),
            "date": str(it.get("date") or "").strip(),
            "source": str(it.get("source") or "").strip(),
            "extrait": str(it.get("extrait") or "").strip(),
        }
        if not (row["titre"] and row["url"]):
            continue
        if not in_window(row["date"], since, today):
            dropped += 1
            continue
        cleaned.append(row)
    for i, c in enumerate(cleaned):
        if not c["id"]:
            c["id"] = f"item-{i+1}"

    payload = {
        "collectedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": cleaned,
    }
    write_json(CANDIDATS_PATH, payload)
    msg = f"{len(cleaned)} candidat(s) → {CANDIDATS_PATH} (fenêtre {since} → {today}"
    if dropped:
        msg += f", {dropped} hors fenêtre écarté(s)"
    print(msg + ")")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        today = date(2026, 11, 11)
        since = today - timedelta(days=WINDOW_DAYS)
        assert in_window("2026-11-03", since, today)
        assert in_window("2026-10-27", since, today)
        assert not in_window("2026-10-26", since, today)
        assert not in_window("2026", since, today)
        assert not in_window("2027-01-28", since, today)
        print("self-check ok")
        raise SystemExit(0)
    main()
