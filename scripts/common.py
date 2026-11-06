"""Chemins et utilitaires partagés (stdlib only)."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCTRINE = ROOT / "doctrine"
WEB = ROOT / "web"
EXPORTS = DATA / "exports"

CANDIDATS_PATH = DATA / "candidats.json"
SELECTION_PATH = DATA / "selection.json"
RETENUS_PATH = DATA / "retenus.json"
RAPPORT_PATH = DATA / "rapport.md"
SOURCES_PATH = ROOT / "sources.json"


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


def api_key() -> str:
    load_dotenv()
    key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not key:
        raise SystemExit(
            "CURSOR_API_KEY manquante. Copiez .env.example vers .env et collez votre clé."
        )
    return key
