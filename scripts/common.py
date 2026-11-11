"""Chemins et utilitaires partagés (stdlib only)."""

import json
import os
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "web")
EXPORTS = os.path.join(DATA, "exports")
TEMPLATE_DOCX = os.path.join(ROOT, "templates", "veille-juridique.docx")

CANDIDATS_PATH = os.path.join(DATA, "candidats.json")
SELECTION_PATH = os.path.join(DATA, "selection.json")
RAPPORT_PATH = os.path.join(DATA, "rapport.md")
SOURCES_PATH = os.path.join(ROOT, "sources.json")
INSTRUCTIONS_PATH = os.path.join(ROOT, "instructions.md")

_MOIS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


def veille_title(day: date | None = None) -> str:
    """Titre d'en-tête / fichier : date du jour, pas la période des articles."""
    d = day or date.today()
    return f"Veille juridique du {d.day} {_MOIS[d.month - 1]} {d.year}"



def load_dotenv(path: str | None = None) -> None:
    env_path = path or os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def read_json(path: str, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read())


def write_json(path: str, data) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def reset_pipeline_json() -> None:
    """Vide candidats + sélection après un export Word réussi."""
    write_json(CANDIDATS_PATH, {"collectedAt": None, "items": []})
    write_json(SELECTION_PATH, {"selectedIds": [], "updatedAt": None})


def load_sources() -> dict:
    if not os.path.isfile(SOURCES_PATH):
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
