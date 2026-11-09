#!/usr/bin/env python3
"""UI locale (stdlib http.server) : collecte, sélection, rapport Word."""

from __future__ import annotations

import json
import mimetypes
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    CANDIDATS_PATH,
    EXPORTS,
    ROOT,
    SELECTION_PATH,
    WEB,
    read_json,
    reset_pipeline_json,
    write_json,
)

PORT = 8787
_SCRIPTS = ROOT / "scripts"
_job_lock = threading.Lock()
# État du job long (collecte / génération) — le POST démarre, GET /api/job suit.
_job: dict = {"status": "idle"}


def _run_scripts(names: list[str]) -> tuple[bool, list[dict]]:
    logs = []
    for name in names:
        proc = subprocess.run(
            [sys.executable, str(_SCRIPTS / name)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        logs.append(
            {
                "cmd": name,
                "code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
        if proc.returncode != 0:
            return False, logs
    return True, logs


def _start_job(kind: str, scripts: list[str]) -> bool:
    """Démarre un job en arrière-plan. False si un autre tourne déjà."""
    if not _job_lock.acquire(blocking=False):
        return False

    def run() -> None:
        global _job
        try:
            ok, logs = _run_scripts(scripts)
            if not ok:
                _job = {"status": "done", "ok": False, "kind": kind, "logs": logs}
                return
            if kind == "collecter":
                data = read_json(CANDIDATS_PATH, default={"items": []})
                _job = {
                    "status": "done",
                    "ok": True,
                    "kind": kind,
                    "count": len(data.get("items") or []),
                    "collectedAt": data.get("collectedAt"),
                    "logs": logs,
                }
                return
            # generer
            reset_pipeline_json()
            exports = sorted(EXPORTS.glob("veille-*.docx")) if EXPORTS.is_dir() else []
            latest = str(exports[-1]) if exports else None
            _job = {
                "status": "done",
                "ok": True,
                "kind": kind,
                "docx": latest,
                "logs": logs,
            }
        except Exception as exc:  # noqa: BLE001 — remonter à l'UI
            _job = {
                "status": "done",
                "ok": False,
                "kind": kind,
                "error": str(exc),
                "logs": [],
            }
        finally:
            _job_lock.release()

    global _job
    _job = {"status": "running", "kind": kind}
    threading.Thread(target=run, daemon=True).start()
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[ui] {args[0]}")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._file(WEB / "index.html")
        if path == "/api/job":
            return self._json(200, _job)
        if path == "/api/candidats":
            data = read_json(CANDIDATS_PATH, default={"collectedAt": None, "items": []})
            return self._json(200, data)
        if path == "/api/selection":
            data = read_json(SELECTION_PATH, default={"selectedIds": [], "updatedAt": None})
            return self._json(200, data)
        if path.startswith("/web/"):
            return self._file(ROOT / path.lstrip("/"))
        if path.startswith("/assets/"):
            return self._file(WEB / path.lstrip("/"))
        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/selection":
            try:
                payload = json.loads(self._read_body().decode("utf-8"))
            except json.JSONDecodeError:
                return self._json(400, {"error": "JSON invalide"})
            ids = payload.get("selectedIds")
            if not isinstance(ids, list):
                return self._json(400, {"error": "selectedIds doit être une liste"})
            ids = [str(x) for x in ids]
            data = {
                "selectedIds": ids,
                "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            write_json(SELECTION_PATH, data)
            return self._json(200, data)
        if path == "/api/collecter":
            if not _start_job("collecter", ["collect.py"]):
                return self._json(409, {"ok": False, "error": "Une tâche est déjà en cours."})
            return self._json(200, {"ok": True, "started": True, "kind": "collecter"})
        if path == "/api/generer":
            if not _start_job("generer", ["rapport.py", "export_docx.py"]):
                return self._json(409, {"ok": False, "error": "Une tâche est déjà en cours."})
            return self._json(200, {"ok": True, "started": True, "kind": "generer"})
        self._json(404, {"error": "Not found"})

    def _file(self, path: Path) -> None:
        path = path.resolve()
        if not str(path).startswith(str(ROOT.resolve())) or not path.is_file():
            return self._send(404, b"Not found", "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or path.suffix in {".js", ".css", ".html", ".json"}:
            ctype = f"{ctype}; charset=utf-8" if "charset" not in ctype else ctype
        self._send(200, path.read_bytes(), ctype)


def main() -> None:
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Veille médecine du travail : {url}")
    print("Ctrl+C pour arrêter.")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
