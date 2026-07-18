/* Recherche de symboles (US2) — hors-ligne, jamais de résultat inventé.
 *
 * Classement déterministe et explicable : préfixe exact > préfixe (casse pliée)
 * > sous-chaîne, puis ordre lexicographique (FR-007). Sans données ou avec un
 * schéma inconnu, le script ne fait rien : la recherche plein-texte du thème
 * reste disponible.
 */
(function () {
  "use strict";

  var ATLAS_SCHEMA = 1;
  var MAX_RESULTS = 30;
  var UI = {
    en: { placeholder: "Search a symbol… (press s)", none: "No result.", open: "Symbols" },
    fr: { placeholder: "Chercher un symbole… (touche s)", none: "Aucun résultat.", open: "Symboles" },
  };

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    var payload = (window.__ATLAS__ || {}).search;
    if (!payload || payload.schema_version !== ATLAS_SCHEMA || !payload.entries) return;
    var entries = payload.entries;
    var lang = (document.documentElement.lang || "en").slice(0, 2);
    var texts = UI[lang] || UI.en;

    function siteBase() {
      var scripts = document.getElementsByTagName("script");
      for (var i = 0; i < scripts.length; i++) {
        var src = scripts[i].getAttribute("src") || "";
        var at = src.indexOf("assets/atlas-search.js");
        if (at >= 0) return src.slice(0, at);
      }
      return "";
    }
    var base = siteBase();

    // -- interface : bouton discret + palette de recherche ---------------------
    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.textContent = "🔎 " + texts.open;
    trigger.setAttribute(
      "style",
      "position:fixed;right:16px;bottom:16px;z-index:60;padding:6px 10px;border-radius:16px;" +
        "border:1px solid rgba(128,128,128,.4);background:var(--md-default-bg-color,#fff);" +
        "color:inherit;cursor:pointer;font-size:.7rem;box-shadow:0 1px 4px rgba(0,0,0,.2);"
    );
    document.body.appendChild(trigger);

    var overlay = document.createElement("div");
    overlay.setAttribute(
      "style",
      "position:fixed;inset:0;z-index:70;display:none;background:rgba(0,0,0,.35);" +
        "align-items:flex-start;justify-content:center;padding-top:10vh;"
    );
    var box = document.createElement("div");
    box.setAttribute(
      "style",
      "width:min(640px,90vw);background:var(--md-default-bg-color,#fff);color:inherit;" +
        "border-radius:8px;box-shadow:0 8px 30px rgba(0,0,0,.35);overflow:hidden;"
    );
    var input = document.createElement("input");
    input.type = "search";
    input.placeholder = texts.placeholder;
    input.setAttribute(
      "style",
      "width:100%;box-sizing:border-box;padding:12px 14px;border:0;outline:none;" +
        "font-size:1rem;background:transparent;color:inherit;"
    );
    var list = document.createElement("div");
    list.setAttribute("style", "max-height:50vh;overflow:auto;border-top:1px solid rgba(128,128,128,.3);");
    box.appendChild(input);
    box.appendChild(list);
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    var results = [];
    var selected = 0;

    function escapeHtml(text) {
      var div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }

    function rank(entry, query, folded) {
      if (entry.name === query) return 0; // préfixe exact (égalité stricte d'abord)
      var name = entry.name.toLowerCase();
      if (name.indexOf(folded) === 0) return 1;
      if (name.indexOf(folded) > 0) return 2;
      if (entry.qualname.toLowerCase().indexOf(folded) >= 0) return 3;
      return -1;
    }

    function search(query) {
      if (!query) return [];
      var folded = query.toLowerCase();
      var scored = [];
      entries.forEach(function (entry) {
        var score = rank(entry, query, folded);
        if (score >= 0) scored.push([score, entry.name, entry.qualname, entry]);
      });
      scored.sort(function (a, b) {
        if (a[0] !== b[0]) return a[0] - b[0];
        if (a[1] !== b[1]) return a[1] < b[1] ? -1 : 1;
        return a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0;
      });
      return scored.slice(0, MAX_RESULTS).map(function (row) {
        return row[3];
      });
    }

    function renderResults() {
      list.innerHTML = "";
      if (!input.value) return;
      if (!results.length) {
        var none = document.createElement("div");
        none.setAttribute("style", "padding:10px 14px;opacity:.7;font-size:.8rem;");
        none.textContent = texts.none; // état vide explicite (FR-008)
        list.appendChild(none);
        return;
      }
      results.forEach(function (entry, index) {
        var row = document.createElement("a");
        row.href = base + entry.page;
        row.setAttribute(
          "style",
          "display:block;padding:8px 14px;text-decoration:none;color:inherit;font-size:.8rem;" +
            (index === selected ? "background:rgba(94,129,244,.18);" : "")
        );
        row.innerHTML =
          "<strong>" + escapeHtml(entry.name) + "</strong>" +
          "<code style='opacity:.75'>" + escapeHtml(entry.signature) + "</code>" +
          " <span style='opacity:.6'>· " + escapeHtml(entry.kind) +
          " · " + escapeHtml(entry.module) + " · " + escapeHtml(entry.language) + "</span>";
        row.addEventListener("mousemove", function () {
          if (selected !== index) {
            selected = index;
            renderResults();
          }
        });
        list.appendChild(row);
      });
    }

    function open() {
      overlay.style.display = "flex";
      input.value = "";
      results = [];
      selected = 0;
      renderResults();
      input.focus();
    }
    function close() {
      overlay.style.display = "none";
    }

    trigger.addEventListener("click", open);
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) close();
    });
    input.addEventListener("input", function () {
      results = search(input.value.trim());
      selected = 0;
      renderResults();
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (selected < results.length - 1) selected += 1;
        renderResults();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        if (selected > 0) selected -= 1;
        renderResults();
      } else if (event.key === "Enter") {
        if (results[selected]) window.location.href = base + results[selected].page;
      } else if (event.key === "Escape") {
        close();
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "s" || overlay.style.display === "flex") return;
      var target = event.target;
      var tag = target && target.tagName ? target.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea" || (target && target.isContentEditable)) return;
      event.preventDefault();
      open();
    });
  });
})();
