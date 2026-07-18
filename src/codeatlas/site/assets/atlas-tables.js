/* Tables triables et filtrables (US4, FR-013) — enrichissement progressif.
 *
 * S'applique à toutes les tables du contenu : clic sur un en-tête = tri stable
 * (numérique quand la colonne s'y prête, sinon lexicographique), second clic =
 * ordre inverse ; un champ de filtre au-dessus de chaque table masque les
 * lignes sans correspondance. Sans JavaScript, les tables restent des tables
 * (FR-005).
 */
(function () {
  "use strict";

  var UI = {
    en: { filter: "Filter rows…" },
    fr: { filter: "Filtrer les lignes…" },
  };

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function cellValue(row, index) {
    var cell = row.cells[index];
    return cell ? cell.textContent.trim() : "";
  }

  function numeric(text) {
    var match = text.replace(",", ".").match(/-?\d+(\.\d+)?/);
    return match ? parseFloat(match[0]) : null;
  }

  function sortTable(table, index, ascending) {
    var body = table.tBodies[0];
    if (!body) return;
    var rows = Array.prototype.slice.call(body.rows);
    var numbers = rows.every(function (row) {
      var text = cellValue(row, index);
      return text === "" || numeric(text) !== null;
    });
    var keyed = rows.map(function (row, position) {
      return { row: row, position: position };
    });
    keyed.sort(function (a, b) {
      var left = cellValue(a.row, index);
      var right = cellValue(b.row, index);
      var result;
      if (numbers) {
        result = (numeric(left) || 0) - (numeric(right) || 0);
      } else {
        result = left < right ? -1 : left > right ? 1 : 0;
      }
      if (result === 0) result = a.position - b.position; // tri stable
      return ascending ? result : -result;
    });
    keyed.forEach(function (entry) {
      body.appendChild(entry.row);
    });
  }

  function attachFilter(table, placeholder) {
    var body = table.tBodies[0];
    if (!body || body.rows.length < 4) return; // filtrer 3 lignes n'aide personne
    var input = document.createElement("input");
    input.type = "search";
    input.placeholder = placeholder;
    input.setAttribute("aria-label", placeholder);
    input.setAttribute("data-atlas-filter", "");
    input.setAttribute(
      "style",
      "display:block;margin:0 0 4px;padding:3px 8px;font-size:.7rem;width:14rem;" +
        "max-width:100%;border:1px solid rgba(128,128,128,.4);border-radius:4px;" +
        "background:transparent;color:inherit;"
    );
    input.addEventListener("input", function () {
      var query = input.value.trim().toLowerCase();
      Array.prototype.forEach.call(body.rows, function (row) {
        var text = row.textContent.toLowerCase();
        row.style.display = !query || text.indexOf(query) >= 0 ? "" : "none";
      });
    });
    table.parentNode.insertBefore(input, table);
  }

  ready(function () {
    var lang = (document.documentElement.lang || "en").slice(0, 2);
    var texts = UI[lang] || UI.en;
    var tables = document.querySelectorAll("article table, .md-typeset table");
    Array.prototype.forEach.call(tables, function (table) {
      if (!table.tHead || !table.tHead.rows.length) return;
      attachFilter(table, texts.filter);
      Array.prototype.forEach.call(table.tHead.rows[0].cells, function (cell, index) {
        if (!cell.textContent.trim()) return;
        cell.style.cursor = "pointer";
        cell.setAttribute("role", "button");
        cell.addEventListener("click", function () {
          var ascending = cell.getAttribute("data-atlas-sort") !== "asc";
          Array.prototype.forEach.call(table.tHead.rows[0].cells, function (other) {
            other.removeAttribute("data-atlas-sort");
          });
          cell.setAttribute("data-atlas-sort", ascending ? "asc" : "desc");
          sortTable(table, index, ascending);
        });
      });
    });
  });
})();
