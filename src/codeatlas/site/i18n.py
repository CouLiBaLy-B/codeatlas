"""Libellés du site généré (FR-017) — le contenu extrait n'est jamais traduit."""

from __future__ import annotations

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "overview": "Overview",
        "modules": "Modules",
        "api": "API reference",
        "classes": "Classes",
        "functions": "Functions",
        "methods": "Methods",
        "attributes": "Attributes",
        "class_diagram": "Class diagram",
        "package_deps": "Package dependencies",
        "cycles": "Dependency cycles",
        "no_cycles": "No dependency cycle detected.",
        "skipped": "Not analyzed",
        "skipped_reason": "Reason",
        "stats": "Statistics",
        "files_analyzed": "Files analyzed",
        "files_skipped": "Files skipped",
        "symbols": "Symbols",
        "relations": "Relations",
        "source": "Source",
        "no_doc": "No documentation.",
        "entry_points": "Entry points",
        "flow_legend": (
            "Solid arrows are statically certain calls; dotted arrows are uncertain "
            "(dynamic) calls."
        ),
        "detected_by": "Detected by",
        "health": "Code health",
        "module": "Module",
        "loc": "Lines",
        "max_complexity": "Max complexity",
        "doc_coverage": "Doc coverage",
        "coupling": "Coupling (in/out)",
        "status": "Status",
        "worst_functions": "Functions above complexity thresholds",
        "dead_code": "Probably dead code",
        "confidence": "Confidence",
        "no_dead_code": "No dead code detected.",
        "global_doc_coverage": "Overall documentation coverage",
        "architecture": "Architecture",
        "architecture_note": (
            "Layers are detected from package naming conventions and dependency "
            "direction; every finding is backed by traceable evidence."
        ),
        "violations": "Layer violations",
        "no_violations": "No layer violation detected.",
        "patterns": "Design patterns",
        "no_patterns": "No design pattern detected.",
        "pattern": "Pattern",
        "evidence": "Evidence",
        "monorepo": "Monorepo",
        "services_graph": "Inter-service dependencies",
        "subprojects": "Sub-projects",
        "subproject": "Sub-project",
        "language": "Language",
        "unsupported": "language not supported — not analyzed",
        "changelog": "Architectural changelog",
        "initial_state": "Initial captured state.",
        "tour": "Reading tour",
        "tour_note": (
            "Suggested onboarding order — entry points first, then layers from "
            "presentation down to infrastructure."
        ),
    },
    "fr": {
        "overview": "Vue d'ensemble",
        "modules": "Modules",
        "api": "Référence API",
        "classes": "Classes",
        "functions": "Fonctions",
        "methods": "Méthodes",
        "attributes": "Attributs",
        "class_diagram": "Diagramme de classes",
        "package_deps": "Dépendances de packages",
        "cycles": "Cycles de dépendances",
        "no_cycles": "Aucun cycle de dépendances détecté.",
        "skipped": "Éléments non analysés",
        "skipped_reason": "Raison",
        "stats": "Statistiques",
        "files_analyzed": "Fichiers analysés",
        "files_skipped": "Fichiers ignorés",
        "symbols": "Symboles",
        "relations": "Relations",
        "source": "Source",
        "no_doc": "Pas de documentation.",
        "entry_points": "Points d'entrée",
        "flow_legend": (
            "Trait plein : appel sûr statiquement ; pointillé : appel incertain "
            "(dynamique)."
        ),
        "detected_by": "Détecté par",
        "health": "Santé du code",
        "module": "Module",
        "loc": "Lignes",
        "max_complexity": "Complexité max",
        "doc_coverage": "Couverture doc",
        "coupling": "Couplage (in/out)",
        "status": "Statut",
        "worst_functions": "Fonctions au-dessus des seuils de complexité",
        "dead_code": "Code probablement mort",
        "confidence": "Confiance",
        "no_dead_code": "Aucun code mort détecté.",
        "global_doc_coverage": "Couverture de documentation globale",
        "architecture": "Architecture",
        "architecture_note": (
            "Les couches sont détectées par convention de nommage des packages et "
            "direction des dépendances ; chaque affirmation porte ses indices."
        ),
        "violations": "Violations de couches",
        "no_violations": "Aucune violation de couches détectée.",
        "patterns": "Design patterns",
        "no_patterns": "Aucun design pattern détecté.",
        "pattern": "Pattern",
        "evidence": "Indices",
        "monorepo": "Monorepo",
        "services_graph": "Dépendances inter-services",
        "subprojects": "Sous-projets",
        "subproject": "Sous-projet",
        "language": "Langage",
        "unsupported": "langage non supporté — non analysé",
        "changelog": "Changelog architectural",
        "initial_state": "État initial capturé.",
        "tour": "Parcours de lecture",
        "tour_note": (
            "Ordre de lecture suggéré pour l'onboarding — points d'entrée d'abord, "
            "puis les couches de la présentation vers l'infrastructure."
        ),
    },
}


def labels(language: str) -> dict[str, str]:
    return LABELS.get(language, LABELS["en"])
