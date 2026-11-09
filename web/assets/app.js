(function () {
  var listEl = document.getElementById("list");
  var panelEl = document.getElementById("panel");
  var spinnerEl = document.getElementById("spinner");
  var emptyMsg = document.getElementById("empty-msg");
  var busyMsg = document.getElementById("busy-msg");
  var itemTpl = document.getElementById("tpl-item");
  var metaEl = document.getElementById("meta");
  var statusEl = document.getElementById("status");
  var btnCollect = document.getElementById("btn-collect");
  var btnGen = document.getElementById("btn-gen");
  var items = [];
  var selected = new Set();
  var busy = false;
  var POLL_MS = 2000;

  function setStatus(msg) {
    statusEl.textContent = msg || "";
  }

  function syncGenEnabled() {
    btnGen.disabled = busy || selected.size === 0;
  }

  function syncPanel() {
    listEl.hidden = busy;
    if (busy) {
      panelEl.hidden = false;
      spinnerEl.hidden = false;
      emptyMsg.hidden = true;
      busyMsg.hidden = false;
      return;
    }
    spinnerEl.hidden = true;
    busyMsg.hidden = true;
    if (items.length) {
      panelEl.hidden = true;
      emptyMsg.hidden = true;
      return;
    }
    panelEl.hidden = false;
    emptyMsg.hidden = false;
  }

  function setBusy(on, msg) {
    busy = !!on;
    if (on) busyMsg.textContent = msg || "";
    syncPanel();
    btnCollect.disabled = on;
    syncGenEnabled();
  }

  function networkHint(e) {
    return (
      "Serveur injoignable (" +
      e +
      "). Relancez l'UI (lancer.bat ou python3 scripts/serve.py) puis rechargez la page."
    );
  }

  function logsText(data) {
    if (!data || !data.logs) return (data && data.error) || JSON.stringify(data || {});
    return data.logs
      .map(function (l) {
        return (l.stderr || l.stdout || "").trim();
      })
      .filter(Boolean)
      .join("\n");
  }

  function formatParis(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return new Intl.DateTimeFormat("fr-FR", {
      timeZone: "Europe/Paris",
      dateStyle: "short",
      timeStyle: "short",
    }).format(d);
  }

  function render() {
    listEl.replaceChildren();
    syncPanel();
    items.forEach(function (it) {
      var id = it.id;
      var node = itemTpl.content.cloneNode(true);
      var input = node.querySelector("input");
      input.checked = selected.has(id);
      input.addEventListener("change", function (e) {
        if (e.target.checked) selected.add(id);
        else selected.delete(id);
        syncGenEnabled();
      });
      node.querySelector('[data-field="titre"]').textContent =
        it.titre || "(sans titre)";
      node.querySelector('[data-field="meta"]').textContent =
        (it.source || "—") + " · " + (it.date || "—");
      node.querySelector('[data-field="extrait"]').textContent = it.extrait || "";
      node.querySelector('[data-field="url"]').href = it.url || "#";
      listEl.appendChild(node);
    });
    syncGenEnabled();
  }

  function load() {
    return Promise.all([
      fetch("/api/candidats").then(function (r) {
        return r.json();
      }),
      fetch("/api/selection").then(function (r) {
        return r.json();
      }),
    ]).then(function (pair) {
      var cand = pair[0];
      var sel = pair[1];
      items = cand.items || [];
      selected = new Set(sel.selectedIds || []);
      metaEl.textContent = cand.collectedAt
        ? "Collecte du " + formatParis(cand.collectedAt) + " — " + items.length + " article(s)"
        : items.length
          ? items.length + " article(s)"
          : "Pas encore de collecte.";
      render();
    });
  }

  function saveSelection() {
    var ids = Array.from(selected);
    return fetch("/api/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selectedIds: ids }),
    }).then(function (r) {
      return r.json();
    });
  }

  function pollJob() {
    return fetch("/api/job")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.status === "running") {
          return new Promise(function (resolve) {
            setTimeout(resolve, POLL_MS);
          }).then(pollJob);
        }
        if (data.status !== "done") {
          return { httpOk: false, data: { ok: false, error: "Pas de tâche en cours." } };
        }
        return { httpOk: !!data.ok, data: data };
      });
  }

  function postJob(url) {
    return fetch(url, { method: "POST" })
      .then(function (r) {
        return r.json().then(function (data) {
          return { httpOk: r.ok, data: data };
        });
      })
      .then(function (res) {
        if (!res.httpOk || !res.data.ok) return res;
        if (res.data.started) return pollJob();
        return res;
      });
  }

  syncGenEnabled();

  btnCollect.onclick = function () {
    if (busy) return;
    setBusy(true, "Collecte selon vos instructions en cours…");
    setStatus("");
    postJob("/api/collecter")
      .then(function (res) {
        if (!res.httpOk || !res.data.ok) {
          setStatus("Échec collecte : " + (res.data.error || logsText(res.data)));
          return;
        }
        selected.clear();
        return load().then(function () {
          setStatus(
            "Collecte terminée — " +
              (res.data.count || items.length) +
              " article(s). Cochez ceux à garder."
          );
        });
      })
      .catch(function (e) {
        setStatus("Erreur collecte : " + networkHint(e));
      })
      .then(function () {
        setBusy(false);
      });
  };

  btnGen.onclick = function () {
    if (busy) return;
    if (!selected.size) {
      setStatus("Cochez au moins un article avant de générer.");
      return;
    }
    setBusy(true, "Rédaction du rapport et export Word en cours…");
    setStatus("");
    saveSelection()
      .then(function () {
        return postJob("/api/generer");
      })
      .then(function (res) {
        if (!res.httpOk || !res.data.ok) {
          setStatus("Échec génération : " + (res.data.error || logsText(res.data)));
          return;
        }
        return load().then(function () {
          setStatus("OK — fichier : " + (res.data.docx || "voir data/exports/"));
        });
      })
      .catch(function (e) {
        setStatus("Erreur génération : " + networkHint(e));
      })
      .then(function () {
        setBusy(false);
      });
  };

  load().catch(function (e) {
    setStatus("Impossible de charger les candidats : " + networkHint(e));
  });
})();
