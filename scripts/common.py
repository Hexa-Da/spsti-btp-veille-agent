"""Chemins et utilitaires partagés (stdlib only)."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"
EXPORTS = DATA / "exports"

CANDIDATS_PATH = DATA / "candidats.json"
SELECTION_PATH = DATA / "selection.json"
RAPPORT_PATH = DATA / "rapport.md"
SOURCES_PATH = ROOT / "sources.json"
INSTRUCTIONS_PATH = ROOT / "instructions.md"


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or (ROOT / ".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def read_json(path: Path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_sources() -> dict:
    if not SOURCES_PATH.is_file():
        raise SystemExit(f"Aucune config sources : {SOURCES_PATH}")
    return read_json(SOURCES_PATH)


def selected_items() -> list[dict]:
    """Candidats cochés (ordre de selection.json)."""
    candidats = read_json(CANDIDATS_PATH)
    selection = read_json(SELECTION_PATH, default={"selectedIds": []})
    if not candidats or not candidats.get("items"):
        raise SystemExit(f"Aucun candidat : lancez d'abord collect.py ({CANDIDATS_PATH})")
    ids = selection.get("selectedIds") or []
    if not ids:
        raise SystemExit("Aucune sélection : ouvrez l'UI et cochez des articles.")
    by_id = {it["id"]: it for it in candidats["items"] if it.get("id")}
    items = []
    for item_id in ids:
        base = by_id.get(item_id)
        if not base:
            print(f"Ignore id inconnu : {item_id}")
            continue
        items.append(
            {
                "id": base.get("id"),
                "titre": base.get("titre"),
                "url": base.get("url"),
                "date": base.get("date"),
                "source": base.get("source"),
                "extrait": base.get("extrait"),
            }
        )
    if not items:
        raise SystemExit("Aucun article sélectionné valide.")
    return items


def api_key() -> str:
    load_dotenv()
    key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not key:
        raise SystemExit(
            "CURSOR_API_KEY manquante. Copiez .env.example vers .env et collez votre clé."
        )
    return key
