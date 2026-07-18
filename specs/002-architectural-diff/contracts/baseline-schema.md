# Contract: Schéma de la baseline (`.codeatlas/baseline.json`)

Format versionné (`baseline_version: 1`), canonique : clés triées, UTF-8, indentation
2, fin de ligne `\n`, listes triées, **aucun horodatage**. Fichier destiné à être
committé et relu en revue.

```json
{
  "baseline_version": 1,
  "ir_version": 1,
  "root": "mon-repo",
  "subprojects": [{ "id": "main", "language": "python" }],
  "public_api": [
    { "id": "main/pkg.mod.Class", "kind": "class", "signature": "" },
    { "id": "main/pkg.mod.Class.method", "kind": "method", "signature": "(x: int) -> str" }
  ],
  "package_cycles": [["pkg.a", "pkg.b"]],
  "layer_violations": [{ "source": "pkg.infra", "target": "pkg.api" }],
  "inferred_calls": [{ "source": "main/pkg.mod.f", "target": "main/pkg.mod.Class.g" }],
  "dead_code": [{ "id": "main/pkg.mod._helper", "confidence": "high" }],
  "service_deps": [{ "source": "front", "target": "shared-lib" }],
  "skipped": [{ "path": "pkg/bad.py", "reason": "SyntaxError: …" }],
  "metrics": {
    "critical_symbols": 1,
    "doc_coverage": 62,
    "edges": 220,
    "files_analyzed": 15,
    "nodes": 80
  }
}
```

## Règles

1. **Compatibilité** : un `baseline_version` inconnu ou un `ir_version` différent de
   celui du CodeAtlas courant → erreur d'usage explicite (exit 2), message invitant à
   recapturer. Jamais de comparaison silencieusement fausse (FR-006).
2. **Emplacements** : défaut `.codeatlas/baseline.json` sous la racine analysée ;
   archives `.codeatlas/history/<label>.json` (label : `[A-Za-z0-9._-]+`).
   `.codeatlas/` n'est jamais analysé (exclusion par défaut).
3. **Public API** : symboles `public` de kinds class/interface/enum/function/method ;
   la signature fait partie de l'identité comparée (changement → apparu+disparu,
   rendu apparié « modifiée »).
4. **Capture** : dérivée exclusivement de `CodeGraph` + insights existants
   (constitution III) ; mêmes définitions que le site (aucune divergence de calcul).
