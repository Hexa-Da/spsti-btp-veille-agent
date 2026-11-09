(function () {
  var listEl = document.getElementById("list");
  var metaEl = document.getElementById("meta");
  var statusEl = document.getElementById("status");
  var busyEl = document.getElementById("busy");
  var busyMsg = document.getElementById("busy-msg");
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

  function setBusy(on, msg) {
    busy = !!on;
    busyEl.hidden = !on;
    busyMsg.textContent = msg || "Patientez…";
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
    if (!items.length) {
      listEl.innerHTML =
        '<div class="empty">Aucun candidat. Cliquez sur <strong>Lancer la Collecte</strong> pour démarrer.</div>';
      return;
    }
    listEl.innerHTML = "";
    items.forEach(function (it) {
      var div = document.createElement("div");
      div.className = "item";
      var id = it.id;
      var checked = selected.has(id) ? " checked" : "";
      var date = it.date || "—";
      var source = it.source || "—";
      var extrait = it.extrait || "";
      var url = it.url || "#";
      div.innerHTML =
        "<label>" +
        '<input type="checkbox" data-id="' +
        id +
        '"' +
        checked +
        ">" +
        "<div>" +
        "<h2></h2>" +
        '<p class="meta"></p>' +
        '<p class="extrait"></p>' +
        '<p><a target="_blank" rel="noopener"></a></p>' +
        "</div></label>";
      div.querySelector("h2").textContent = it.titre || "(sans titre)";
      div.querySelector(".meta").textContent = source + " · " + date;
      div.querySelector(".extrait").textContent = extrait;
      var a = div.querySelector("a");
      a.href = url;
      a.textContent = "Ouvrir la source";
      div.querySelector("input").addEventListener("change", function (e) {
        if (e.target.checked) selected.add(id);
        else selected.delete(id);
        syncGenEnabled();
      });
      listEl.appendChild(div);
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
    setBusy(true, "Collecte + tri en cours… Cela peut prendre plusieurs minutes.");
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
    setBusy(true, "Résumé agent + export Word… Cela peut prendre plusieurs minutes.");
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
