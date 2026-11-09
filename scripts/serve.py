#!/usr/bin/env python3
"""UI locale (stdlib http.server) : collecte, sélection, rapport Word."""

import json
import mimetypes
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
_SCRIPTS = os.path.join(ROOT, "scripts")
_busy = threading.Lock()


def _run_scripts(names: list[str]) -> tuple[bool, list[dict]]:
    logs = []
    for name in names:
        proc = subprocess.run(
            [sys.executable, os.path.join(_SCRIPTS, name)],
            cwd=ROOT,
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


def _run_action(kind: str, scripts: list[str]) -> tuple[int, dict]:
    """Exécute les scripts et renvoie (code HTTP, payload JSON)."""
    if not _busy.acquire(blocking=False):
        return 409, {"ok": False, "error": "Une tâche est déjà en cours."}
    try:
        ok, logs = _run_scripts(scripts)
        if not ok:
            return 200, {"ok": False, "kind": kind, "logs": logs}
        if kind == "collecter":
            data = read_json(CANDIDATS_PATH, default={"items": []})
            return 200, {
                "ok": True,
                "kind": kind,
                "count": len(data.get("items") or []),
                "collectedAt": data.get("collectedAt"),
                "logs": logs,
            }
        reset_pipeline_json()
        if os.path.isdir(EXPORTS):
            exports = sorted(
                os.path.join(EXPORTS, name)
                for name in os.listdir(EXPORTS)
                if name.startswith("veille-") and name.endswith(".docx")
            )
        else:
            exports = []
        return 200, {
            "ok": True,
            "kind": kind,
            "docx": exports[-1] if exports else None,
            "logs": logs,
        }
    except Exception as exc:  # noqa: BLE001 — remonter à l'UI
        return 200, {"ok": False, "kind": kind, "error": str(exc), "logs": []}
    finally:
        _busy.release()


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
            return self._file(os.path.join(WEB, "index.html"))
        if path == "/api/candidats":
            data = read_json(CANDIDATS_PATH, default={"collectedAt": None, "items": []})
            return self._json(200, data)
        if path == "/api/selection":
            data = read_json(SELECTION_PATH, default={"selectedIds": [], "updatedAt": None})
            return self._json(200, data)
        if path.startswith("/web/"):
            return self._file(os.path.join(ROOT, path.lstrip("/")))
        if path.startswith("/assets/"):
            return self._file(os.path.join(WEB, path.lstrip("/")))
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
            code, data = _run_action("collecter", ["collect.py"])
            return self._json(code, data)
        if path == "/api/generer":
            code, data = _run_action("generer", ["rapport.py", "export_docx.py"])
            return self._json(code, data)
        self._json(404, {"error": "Not found"})

    def _file(self, path: str) -> None:
        root = os.path.abspath(ROOT)
        path = os.path.abspath(path)
        if not (path == root or path.startswith(root + os.sep)) or not os.path.isfile(path):
            return self._send(404, b"Not found", "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        ext = os.path.splitext(path)[1]
        if ctype.startswith("text/") or ext in {".js", ".css", ".html", ".json"}:
            ctype = f"{ctype}; charset=utf-8" if "charset" not in ctype else ctype
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype)


def main() -> None:
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Veille médecine du travail : {url}")
    print("Ctrl+C pour arrêter.")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
