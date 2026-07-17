/* Initialisation du rendu Mermaid — 100 % local, aucun CDN (SC-007). */
if (typeof mermaid !== "undefined") {
  mermaid.initialize({ startOnLoad: true, securityLevel: "loose", theme: "neutral" });
}
