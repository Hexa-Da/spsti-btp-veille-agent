(function () {
  const listEl = document.getElementById("list");
  const panelEl = document.getElementById("panel");
  const spinnerEl = document.getElementById("spinner");
  const emptyMsg = document.getElementById("empty-msg");
  const busyMsg = document.getElementById("busy-msg");
  const itemTpl = document.getElementById("tpl-item");
  const metaEl = document.getElementById("meta");
  const btnCollect = document.getElementById("btn-collect");
  const btnToggle = document.getElementById("btn-toggle");
  const btnGen = document.getElementById("btn-gen");
  let items = [];
  let selected = new Set();
  let busy = false;
  let hasCollected = false;

  function syncCollectEnabled() {
    btnCollect.disabled = busy || hasCollected;
  }

  function syncToggle() {
    const allOn = items.length > 0 && selected.size === items.length;
    btnToggle.disabled = busy || items.length === 0;
    btnToggle.textContent = allOn ? "Tout décocher" : "Tout cocher";
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
    busy = on;
    if (on) busyMsg.textContent = msg;
    syncPanel();
    syncCollectEnabled();
    syncToggle();
    syncGenEnabled();
  }

  function formatParis(iso) {
    return new Intl.DateTimeFormat("fr-FR", {
      timeZone: "Europe/Paris",
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  }

  function render() {
    listEl.replaceChildren();
    syncPanel();
    items.forEach(function (it) {
      const id = it.id;
      const node = itemTpl.content.cloneNode(true);
      const input = node.querySelector("input");
      input.checked = selected.has(id);
      input.addEventListener("change", function (e) {
        if (e.target.checked) selected.add(id);
        else selected.delete(id);
        syncToggle();
        syncGenEnabled();
      });
      node.querySelector('[data-field="titre"]').textContent = it.titre;
      node.querySelector('[data-field="extrait"]').textContent = it.extrait;
      node.querySelector('[data-field="url"]').href = it.url;
      node.querySelector('[data-field="meta"]').textContent = it.source + " le " + it.date;
      listEl.appendChild(node);
    });
  }

  function load() {
    return fetch("/api/candidats")
      .then(function (r) {
        return r.json();
      })
      .then(function (candidats) {
        items = candidats.items;
        selected = new Set();
        hasCollected = Boolean(candidats.collectedAt);
        metaEl.textContent = hasCollected
          ? "Collecte du " + formatParis(candidats.collectedAt) + " — " + items.length + " article(s)"
          : "Pas encore de collecte.";
        render();
        syncCollectEnabled();
        syncToggle();
        syncGenEnabled();
      });
  }

  btnToggle.onclick = function () {
    if (selected.size === items.length) selected = new Set();
    else selected = new Set(items.map(function (it) { return it.id; }));
    render();
    syncToggle();
    syncGenEnabled();
  };

  function postAction(url) {
    return fetch(url, { method: "POST" }).then(function (r) {
      return r.json().then(function (data) {
        return r.ok && data.ok;
      });
    });
  }

  btnCollect.onclick = function () {
    setBusy(true, "Collecte selon vos instructions en cours…");
    postAction("/api/collecter")
      .then(function (ok) {
        if (ok) return load();
      })
      .finally(function () {
        setBusy(false);
      });
  };

  btnGen.onclick = function () {
    setBusy(true, "Rédaction du rapport et export Word en cours…");
    fetch("/api/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selectedIds: Array.from(selected) }),
    })
      .then(function () {
        return postAction("/api/generer");
      })
      .then(function (ok) {
        if (ok) return load();
      })
      .finally(function () {
        setBusy(false);
      });
  };

  load();
})();
