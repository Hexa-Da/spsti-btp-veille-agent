(function () {
  var listEl = document.getElementById("list");
  var metaEl = document.getElementById("meta");
  var statusEl = document.getElementById("status");
  var items = [];
  var selected = new Set();

  function setStatus(msg) {
    statusEl.textContent = msg || "";
  }

  function render() {
    if (!items.length) {
      listEl.innerHTML =
        '<div class="empty">Aucun candidat. Lancez d’abord <code>01-collecter.bat</code> (ou <code>python scripts/collect.py</code>).</div>';
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
      });
      listEl.appendChild(div);
    });
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
        ? "Collecte du " + cand.collectedAt + " — " + items.length + " article(s)"
        : items.length + " article(s)";
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

  document.getElementById("btn-all").onclick = function () {
    items.forEach(function (it) {
      selected.add(it.id);
    });
    render();
  };
  document.getElementById("btn-none").onclick = function () {
    selected.clear();
    render();
  };
  document.getElementById("btn-save").onclick = function () {
    setStatus("Enregistrement…");
    saveSelection()
      .then(function () {
        setStatus("Sélection enregistrée (" + selected.size + ").");
      })
      .catch(function (e) {
        setStatus("Erreur : " + e);
      });
  };
  document.getElementById("btn-gen").onclick = function () {
    var btn = document.getElementById("btn-gen");
    btn.disabled = true;
    setStatus("Enrichissement + résumé agent + Word… (peut prendre plusieurs minutes)");
    saveSelection()
      .then(function () {
        return fetch("/api/generer", { method: "POST" });
      })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, data: data };
        });
      })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok || !res.data.ok) {
          var err =
            (res.data.logs &&
              res.data.logs
                .map(function (l) {
                  return l.stderr || l.stdout || "";
                })
                .join("\n")) ||
            JSON.stringify(res.data);
          setStatus("Échec : " + err);
          return;
        }
        setStatus("OK — fichier : " + (res.data.docx || "voir data/exports/"));
      })
      .catch(function (e) {
        btn.disabled = false;
        setStatus("Erreur : " + e);
      });
  };

  load().catch(function (e) {
    setStatus("Impossible de charger les candidats : " + e);
  });
})();
