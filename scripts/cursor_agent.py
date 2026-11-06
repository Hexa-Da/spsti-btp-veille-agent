"""Client HTTP minimal Cloud Agents API (stdlib). Une seule implémentation pour collect + rapport."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

API_BASE = "https://api.cursor.com/v1"


def _request(
    method: str,
    path: str,
    api_key: str,
    body: dict | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"API Cursor {method} {path} → HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"API Cursor injoignable : {e}") from e


def run_prompt(
    api_key: str,
    prompt_text: str,
    *,
    poll_seconds: float = 5.0,
    max_wait_seconds: float = 600.0,
) -> str:
    """Crée un agent cloud sans repo, attend la fin du run, retourne le texte résultat."""
    created = _request(
        "POST",
        "/agents",
        api_key,
        {
            "prompt": {"text": prompt_text},
            # pas de repos : agent sans dépôt, prompt auto-contenu
        },
        timeout=120.0,
    )
    agent = created.get("agent") or {}
    run = created.get("run") or {}
    agent_id = agent.get("id")
    run_id = run.get("id") or agent.get("latestRunId")
    if not agent_id or not run_id:
        raise SystemExit(f"Réponse API inattendue à la création : {created!r}")

    deadline = time.time() + max_wait_seconds
    terminal = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}
    while time.time() < deadline:
        status_payload = _request(
            "GET",
            f"/agents/{agent_id}/runs/{run_id}",
            api_key,
            timeout=60.0,
        )
        status = (status_payload.get("status") or "").upper()
        if status in terminal:
            if status != "FINISHED":
                raise SystemExit(
                    f"Run agent terminé en {status} : {status_payload.get('result') or status_payload}"
                )
            result = status_payload.get("result")
            if not result or not str(result).strip():
                raise SystemExit("Run FINISHED mais résultat vide.")
            return str(result).strip()
        time.sleep(poll_seconds)

    raise SystemExit(f"Timeout après {max_wait_seconds:.0f}s (agent={agent_id}, run={run_id}).")


def extract_json_block(text: str) -> Any:
    """Extrait le premier objet/tableau JSON d'une réponse agent (éventuellement entourée de markdown)."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # retire fences ```json ... ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise SystemExit("Impossible d'extraire du JSON de la réponse agent.")
