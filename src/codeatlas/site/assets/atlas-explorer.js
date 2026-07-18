/* Explorateur d'architecture (US1) — 100 % local, aucune requête réseau.
 *
 * Enrichissement progressif : sans ce script (ou si le schéma des données est
 * inconnu), la page garde son contenu statique (FR-005). Toute l'intelligence
 * (niveaux, positions) est précalculée au build ; ici on ne fait que rendre,
 * filtrer et déplier. L'état des filtres vit dans location.hash (partageable).
 */
(function () {
  "use strict";

  var ATLAS_SCHEMA = 1;
  var PALETTE = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4"];

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    var container = document.getElementById("atlas-explorer");
    var data = (window.__ATLAS__ || {}).graph;
    if (!container || typeof cytoscape === "undefined" || !data) return;
    if (data.schema_version !== ATLAS_SCHEMA) return; // repli statique poli

    var labels = {};
    try {
      labels = JSON.parse(container.getAttribute("data-labels") || "{}");
    } catch (e) {
      labels = {};
    }
    function t(key, fallback) {
      return labels[key] || fallback;
    }

    var nodesById = {};
    data.nodes.forEach(function (n) {
      nodesById[n.id] = n;
    });

    // Descendants modules de chaque conteneur (pour filtres et agrégation).
    var childrenOf = {};
    data.nodes.forEach(function (n) {
      if (n.parent) {
        (childrenOf[n.parent] = childrenOf[n.parent] || []).push(n.id);
      }
    });
    var moduleDescendants = {};
    function collectModules(id) {
      if (moduleDescendants[id]) return moduleDescendants[id];
      var node = nodesById[id];
      if (node.level === "module") return (moduleDescendants[id] = [id]);
      var acc = [];
      (childrenOf[id] || []).forEach(function (child) {
        acc = acc.concat(collectModules(child));
      });
      return (moduleDescendants[id] = acc);
    }
    data.nodes.forEach(function (n) {
      collectModules(n.id);
    });

    // -- état : dépliage + filtres (filtres encodés dans le hash, FR-004) ------
    var expanded = {};
    var subprojects = data.nodes.filter(function (n) {
      return n.level === "subproject";
    });
    if (subprojects.length === 1) {
      expanded[subprojects[0].id] = true;
      var pkgs = childrenOf[subprojects[0].id] || [];
      if (pkgs.length === 1) expanded[pkgs[0]] = true;
    }

    var FILTER_KEYS = ["language", "layer", "subproject"];
    var HASH_KEYS = { language: "lang", layer: "layer", subproject: "sub" };
    var filters = { language: "", layer: "", subproject: "" };

    function readHash() {
      var params = new URLSearchParams((location.hash || "#").slice(1));
      FILTER_KEYS.forEach(function (key) {
        filters[key] = params.get(HASH_KEYS[key]) || "";
      });
    }
    function writeHash() {
      var params = new URLSearchParams();
      FILTER_KEYS.forEach(function (key) {
        if (filters[key]) params.set(HASH_KEYS[key], filters[key]);
      });
      var encoded = params.toString();
      history.replaceState(null, "", encoded ? "#" + encoded : location.pathname + location.search);
    }

    function modulePasses(id) {
      var node = nodesById[id];
      return FILTER_KEYS.every(function (key) {
        return !filters[key] || node[key] === filters[key];
      });
    }
    function nodePasses(node) {
      return moduleDescendants[node.id].some(modulePasses);
    }
    function ancestorsExpanded(node) {
      var parent = node.parent;
      while (parent) {
        if (!expanded[parent]) return false;
        parent = nodesById[parent].parent;
      }
      return true;
    }
    function isVisible(node) {
      if (!nodePasses(node)) return false;
      if (!ancestorsExpanded(node)) return false;
      return node.level === "module" || !expanded[node.id];
    }
    function visibleRep(moduleId) {
      var node = nodesById[moduleId];
      if (!nodePasses(node)) return null;
      if (isVisible(node)) return moduleId;
      var parent = node.parent;
      while (parent) {
        if (isVisible(nodesById[parent])) return parent;
        parent = nodesById[parent].parent;
      }
      return null;
    }

    // -- interface : barre de filtres + zone graphe + fiche latérale -----------
    container.innerHTML = "";
    container.setAttribute("style", "display:flex;flex-direction:column;gap:8px;");
    var toolbar = document.createElement("div");
    toolbar.setAttribute("style", "display:flex;gap:8px;flex-wrap:wrap;align-items:center;");
    var body = document.createElement("div");
    body.setAttribute("style", "display:flex;gap:8px;align-items:stretch;");
    var graphHost = document.createElement("div");
    graphHost.setAttribute(
      "style",
      "flex:1;min-height:480px;height:60vh;border:1px solid rgba(128,128,128,.35);border-radius:6px;"
    );
    var panel = document.createElement("aside");
    panel.setAttribute(
      "style",
      "width:280px;max-height:60vh;overflow:auto;border:1px solid rgba(128,128,128,.35);" +
        "border-radius:6px;padding:10px;font-size:.72rem;display:none;"
    );
    body.appendChild(graphHost);
    body.appendChild(panel);
    container.appendChild(toolbar);
    container.appendChild(body);

    function distinctValues(key) {
      var seen = {};
      data.nodes.forEach(function (n) {
        if (n.level === "module" && n[key]) seen[n[key]] = true;
      });
      return Object.keys(seen).sort();
    }
    var selects = {};
    FILTER_KEYS.forEach(function (key) {
      var values = distinctValues(key);
      if (!values.length) return;
      var select = document.createElement("select");
      select.setAttribute("aria-label", t(key, key));
      select.setAttribute("style", "font-size:.72rem;padding:2px 4px;");
      var all = document.createElement("option");
      all.value = "";
      all.textContent = t(key, key) + " : " + t("all", "all");
      select.appendChild(all);
      values.forEach(function (value) {
        var option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
      select.addEventListener("change", function () {
        filters[key] = select.value;
        writeHash();
        render();
      });
      toolbar.appendChild(select);
      selects[key] = select;
    });
    var hint = document.createElement("span");
    hint.setAttribute("style", "font-size:.68rem;opacity:.7;");
    hint.textContent = t("hint", "");
    toolbar.appendChild(hint);

    function syncSelects() {
      FILTER_KEYS.forEach(function (key) {
        if (selects[key]) selects[key].value = filters[key];
      });
    }

    // -- rendu cytoscape (positions précalculées : layout "preset") ------------
    var subIds = subprojects.map(function (n) {
      return n.id;
    });
    function colorOf(node) {
      var index = subIds.indexOf("sub:" + node.subproject);
      return PALETTE[(index >= 0 ? index : 0) % PALETTE.length];
    }
    function sizeOf(node) {
      var loc = (node.metrics && node.metrics.loc) || 0;
      return Math.min(30 + Math.sqrt(loc) * 2, 90);
    }

    var cy = cytoscape({
      container: graphHost,
      elements: [],
      layout: { name: "preset" },
      wheelSensitivity: 0.2,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": 11,
            color: "#666",
            "text-valign": "bottom",
            "text-margin-y": 4,
            "background-color": "data(color)",
            width: "data(size)",
            height: "data(size)",
          },
        },
        {
          selector: "node[level != 'module']",
          style: {
            shape: "round-rectangle",
            "border-width": 2,
            "border-color": "#666",
            "font-weight": "bold",
          },
        },
        {
          selector: "node[?degraded]",
          style: { "border-width": 3, "border-style": "dashed", "border-color": "#e6a23c" },
        },
        {
          selector: "node:selected",
          style: { "border-width": 3, "border-color": "#1e88e5" },
        },
        {
          selector: "edge",
          style: {
            width: "data(width)",
            "line-color": "#9e9e9e",
            "target-arrow-color": "#9e9e9e",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.8,
          },
        },
        { selector: "edge[!certain]", style: { "line-style": "dashed" } },
        { selector: "edge[kind = 'service']", style: { "line-color": "#5470c6", width: 3 } },
      ],
    });

    function buildElements() {
      var elements = [];
      var visible = {};
      data.nodes.forEach(function (node) {
        if (!isVisible(node)) return;
        visible[node.id] = true;
        elements.push({
          group: "nodes",
          data: {
            id: node.id,
            label: node.label,
            level: node.level,
            degraded: !!node.degraded,
            color: colorOf(node),
            size: sizeOf(node),
          },
          position: { x: node.pos.x, y: node.pos.y },
        });
      });
      var aggregated = {};
      data.edges.forEach(function (edge) {
        var source, target;
        if (edge.kind === "service") {
          source = visible[edge.source] ? edge.source : null;
          target = visible[edge.target] ? edge.target : null;
        } else {
          source = visibleRep(edge.source);
          target = visibleRep(edge.target);
        }
        if (!source || !target || source === target) return;
        var key = source + "|" + target + "|" + edge.kind;
        var entry = aggregated[key];
        if (!entry) {
          entry = aggregated[key] = {
            source: source,
            target: target,
            kind: edge.kind,
            certain: true,
            weight: 0,
          };
        }
        entry.weight += edge.weight;
        if (!edge.certain) entry.certain = false;
      });
      Object.keys(aggregated)
        .sort()
        .forEach(function (key, index) {
          var entry = aggregated[key];
          elements.push({
            group: "edges",
            data: {
              id: "e" + index,
              source: entry.source,
              target: entry.target,
              kind: entry.kind,
              certain: entry.certain,
              weight: entry.weight,
              width: Math.min(1.5 + Math.log(entry.weight) * 1.2, 6),
            },
          });
        });
      return elements;
    }

    function render(fit) {
      cy.batch(function () {
        cy.elements().remove();
        cy.add(buildElements());
      });
      if (fit) cy.fit(undefined, 40);
    }

    // -- fiche latérale ---------------------------------------------------------
    function escapeHtml(text) {
      var div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }
    function siteBase() {
      var scripts = document.getElementsByTagName("script");
      for (var i = 0; i < scripts.length; i++) {
        var src = scripts[i].getAttribute("src") || "";
        var at = src.indexOf("assets/atlas-explorer.js");
        if (at >= 0) return src.slice(0, at);
      }
      return "";
    }
    var base = siteBase();

    function neighborRows(nodeId, direction) {
      var rows = {};
      cy.edges().forEach(function (edge) {
        var other = null;
        if (direction === "out" && edge.data("source") === nodeId) other = edge.data("target");
        if (direction === "in" && edge.data("target") === nodeId) other = edge.data("source");
        if (other) rows[other] = (rows[other] || 0) + edge.data("weight");
      });
      return Object.keys(rows)
        .sort()
        .map(function (id) {
          return { id: id, label: nodesById[id].label, weight: rows[id] };
        });
    }

    function showCard(nodeId) {
      var node = nodesById[nodeId];
      var html = "<strong>" + escapeHtml(node.label) + "</strong><br>";
      html += "<em>" + escapeHtml(node.level) + "</em>";
      [["language", node.language], ["layer", node.layer], ["subproject", node.subproject]].forEach(
        function (pair) {
          if (pair[1]) {
            html +=
              "<br>" + escapeHtml(t(pair[0], pair[0])) + " : <code>" + escapeHtml(pair[1]) + "</code>";
          }
        }
      );
      html += "<table style='margin-top:6px'>";
      Object.keys(node.metrics)
        .sort()
        .forEach(function (metric) {
          html +=
            "<tr><td>" + escapeHtml(t(metric, metric)) + "</td><td style='text-align:right'>" +
            node.metrics[metric] + "</td></tr>";
        });
      html += "</table>";
      ["in", "out"].forEach(function (direction) {
        var rows = neighborRows(nodeId, direction);
        if (!rows.length) return;
        html += "<p style='margin:.5em 0 .2em'><strong>" +
          escapeHtml(t("deps_" + direction, direction)) + "</strong></p>";
        rows.forEach(function (row) {
          html +=
            "<a href='#' data-goto='" + escapeHtml(row.id) + "' style='display:block'>" +
            escapeHtml(row.label) + " (" + row.weight + ")</a>";
        });
      });
      html += "<p style='margin-top:8px'>";
      if (node.page) {
        html +=
          "<a href='" + base + node.page + "'>" + escapeHtml(t("open_page", "page")) + "</a> ";
      }
      if (node.level !== "module") {
        html += "<button type='button' data-expand='" + escapeHtml(node.id) + "'>" +
          escapeHtml(t("expand", "+")) + "</button> ";
      }
      if (node.parent) {
        html += "<button type='button' data-collapse='" + escapeHtml(node.parent) + "'>" +
          escapeHtml(t("collapse", "-")) + "</button>";
      }
      html += "</p>";
      panel.innerHTML = html;
      panel.style.display = "block";
    }

    panel.addEventListener("click", function (event) {
      var target = event.target;
      var goto = target.getAttribute && target.getAttribute("data-goto");
      if (goto) {
        event.preventDefault();
        var element = cy.getElementById(goto);
        if (element.length) {
          cy.elements().unselect();
          element.select();
          cy.animate({ center: { eles: element } }, { duration: 150 });
          showCard(goto);
        }
        return;
      }
      var expandId = target.getAttribute && target.getAttribute("data-expand");
      if (expandId) {
        expanded[expandId] = true;
        render();
        return;
      }
      var collapseId = target.getAttribute && target.getAttribute("data-collapse");
      if (collapseId) {
        delete expanded[collapseId];
        var stack = [collapseId];
        while (stack.length) {
          (childrenOf[stack.pop()] || []).forEach(function (child) {
            delete expanded[child];
            stack.push(child);
          });
        }
        render();
        showCard(collapseId);
      }
    });

    cy.on("tap", "node", function (event) {
      showCard(event.target.id());
    });
    cy.on("dbltap", "node", function (event) {
      var node = nodesById[event.target.id()];
      if (node.level !== "module") {
        expanded[node.id] = true;
        render();
      }
    });
    cy.on("tap", function (event) {
      if (event.target === cy) panel.style.display = "none";
    });

    window.addEventListener("hashchange", function () {
      readHash();
      syncSelects();
      render();
    });

    readHash();
    syncSelects();
    render(true);
  });
})();
