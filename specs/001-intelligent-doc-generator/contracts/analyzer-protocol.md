# Contract: Protocole des analyseurs et des insights

## LanguageAnalyzer (point d'extension langage)

Ajouter un langage = implémenter ce protocole et l'enregistrer. Aucune modification du
cœur (constitution III).

```python
class LanguageAnalyzer(Protocol):
    """Contrat d'un analyseur de langage."""

    language: ClassVar[str]              # "python", "javascript", "java"…
    extensions: ClassVar[frozenset[str]] # {".py"}, {".js", ".jsx", ".ts", ".tsx"}…
    manifests: ClassVar[frozenset[str]]  # {"pyproject.toml", "setup.py"}…

    def analyze(self, files: Sequence[SourceFile], subproject: SubProject,
                options: AnalyzerOptions) -> IRFragment:
        """Produit un fragment d'IR (nœuds + arêtes + skipped).

        Obligations :
        - respecte les règles de construction de contracts/ir-schema.md
          (ids stables, chemins POSIX relatifs, tri, certitude honnête) ;
        - ne lève JAMAIS pour un fichier invalide : entrée `skipped` (constitution IV) ;
        - pur : pas de réseau, pas d'exécution du code analysé, pas d'état global.
        """
```

- `SourceFile` : chemin relatif + contenu (lecture faite par le cœur — encodage géré
  centralement, erreurs → `skipped`).
- `AnalyzerOptions` : include_private, motifs d'exclusion déjà appliqués en amont.
- Enregistrement : `analyzers.base.register(analyzer)` ; les extras absents (ex.
  tree-sitter non installé) rendent le langage indisponible avec message actionnable
  (`pip install codeatlas[javascript]`), sans casser le reste.

## EntryPointRecognizer (point d'extension framework)

```python
class EntryPointRecognizer(Protocol):
    language: ClassVar[str]      # langage concerné
    framework: ClassVar[str]     # "fastapi", "click", "spring", "main"…

    def recognize(self, graph: CodeGraph) -> Iterable[Detection]:
        """Détections kind=entrypoint avec evidence (décorateur, annotation,
        signature main…) — opère uniquement sur l'IR."""
```

Reconnaisseurs v1 : Python (`__main__`, click/typer/argparse, fastapi/flask/django) ;
JS/TS (express/nest/fastify, bin de package.json) ; Java (main, spring-web, JAX-RS).

## Insight (métriques, détections)

```python
class Insight(Protocol):
    name: ClassVar[str]  # "metrics", "deadcode", "architecture", "patterns"

    def compute(self, graph: CodeGraph, config: InsightConfig) -> InsightResult:
        """Metrics et/ou Detections. Ne consomme QUE l'IR (+ graph/ algorithmes).
        Déterministe : mêmes entrées → mêmes résultats, listes triées."""
```

Toute `Detection` DOIT porter ≥ 1 `evidence` traçable (id de nœud/arête + explication)
— une détection sans preuve est un bug (FR-013).

## Renderer

```python
class DiagramRenderer(Protocol):
    def render(self, graph: CodeGraph, spec: DiagramSpec) -> Diagram:
        """Texte Mermaid déterministe : éléments triés, ids échappés,
        arêtes `inferred` stylées en pointillés + légende."""
```

## API bibliothèque publique (`codeatlas.api`)

Surface minimale garantie (constitution II) — la CLI n'utilise que ceci :

```python
def analyze(path: Path, config: Config | None = None) -> CodeGraph: ...
def build_site(graph: CodeGraph, out: Path, config: Config | None = None) -> AnalysisReport: ...
def render_diagram(graph: CodeGraph, spec: DiagramSpec) -> Diagram: ...
def run_checks(graph: CodeGraph, thresholds: CheckConfig) -> list[CheckResult]: ...
```

Stabilité : ces signatures sont semver-versionnées avec le package ; tout breaking
change = version majeure.
