#!/usr/bin/env python3
"""Enchaîne enrich → rapport → export (après sélection)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


def run(name: str) -> None:
    print(f"=== {name} ===", flush=True)
    proc = subprocess.run([sys.executable, str(SCRIPTS / name)], cwd=str(ROOT))
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> None:
    run("enrich.py")
    run("rapport.py")
    run("export_docx.py")
    print("Terminé.")


if __name__ == "__main__":
    main()
