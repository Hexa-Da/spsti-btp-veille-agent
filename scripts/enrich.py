#!/usr/bin/env python3
"""Télécharge le corps des articles sélectionnés seulement → data/retenus.json."""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    CANDIDATS_PATH,
    RETENUS_PATH,
    SELECTION_PATH,
    read_json,
    write_json,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


def fetch_text(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "veille-medecine-travail/0.1 (+local)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = "utf-8"
            ctype = resp.headers.get_content_charset()
            if ctype:
                charset = ctype
            html = raw.decode(charset, errors="replace")
    except urllib.error.URLError as e:
        return f"[Erreur de téléchargement : {e}]"
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return html[:8000]
    text = parser.text()
    # shortcut: HTML hétérogène, tronquer pour le prompt rapport
    return text[:12000] if text else html[:8000]


def main() -> None:
    candidats = read_json(CANDIDATS_PATH)
    selection = read_json(SELECTION_PATH, default={"selectedIds": []})
    if not candidats or not candidats.get("items"):
        raise SystemExit(f"Aucun candidat : lancez d'abord collect.py ({CANDIDATS_PATH})")
    ids = selection.get("selectedIds") or []
    if not ids:
        raise SystemExit("Aucune sélection : ouvrez l'UI et cochez des articles.")

    by_id = {it["id"]: it for it in candidats["items"] if it.get("id")}
    retenus = []
    for item_id in ids:
        base = by_id.get(item_id)
        if not base:
            print(f"Ignore id inconnu : {item_id}")
            continue
        print(f"Enrichissement : {base.get('titre', item_id)[:80]}…", flush=True)
        corps = fetch_text(base["url"])
        retenus.append({**base, "corps": corps})

    write_json(
        RETENUS_PATH,
        {
            "updatedAt": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": retenus,
        },
    )
    print(f"{len(retenus)} retenu(s) → {RETENUS_PATH}")


if __name__ == "__main__":
    main()
