"""T002/T003/T008 — Détection de la racine d'import et nommage des modules (US1/US2)."""

from __future__ import annotations

from codeatlas.analyzers.python.analyzer import module_qualname
from codeatlas.analyzers.python.import_root import detect_import_roots

# -- module_qualname(path, import_root) --------------------------------------


def test_qualname_without_root_is_historic_behaviour() -> None:
    assert module_qualname("shopdemo/api.py") == ("shopdemo.api", False)
    assert module_qualname("shopdemo/__init__.py") == ("shopdemo", True)


def test_qualname_strips_import_root_prefix() -> None:
    assert module_qualname("src/mypkg/api.py", "src") == ("mypkg.api", False)
    assert module_qualname("src/mypkg/__init__.py", "src") == ("mypkg", True)
    assert module_qualname("src/mypkg/models/order.py", "src") == ("mypkg.models.order", False)


def test_qualname_nested_import_root() -> None:
    assert module_qualname("a/b/pkg/mod.py", "a/b") == ("pkg.mod", False)


# -- detect_import_roots(paths) ----------------------------------------------


def _src_layout() -> list[str]:
    return [
        "src/mypkg/__init__.py",
        "src/mypkg/core.py",
        "src/mypkg/util.py",
        "src/mypkg/models/__init__.py",
        "src/mypkg/models/order.py",
    ]


def test_src_layout_detects_src_as_root() -> None:
    roots = detect_import_roots(_src_layout())
    assert set(roots.values()) == {"src"}
    # → module_qualname retirera `src`, donnant des noms `mypkg.*`
    assert module_qualname("src/mypkg/core.py", roots["src/mypkg/core.py"]) == ("mypkg.core", False)


def test_package_at_analysis_root_has_empty_import_root() -> None:
    paths = ["shopdemo/__init__.py", "shopdemo/api.py", "shopdemo/models/__init__.py",
             "shopdemo/models/order.py"]
    roots = detect_import_roots(paths)
    assert set(roots.values()) == {""}  # racine vide → comportement historique, zéro régression


def test_package_in_arbitrary_subdirectory() -> None:
    paths = ["lib/mypkg/__init__.py", "lib/mypkg/core.py"]
    roots = detect_import_roots(paths)
    assert roots["lib/mypkg/core.py"] == "lib"
    assert module_qualname("lib/mypkg/core.py", "lib") == ("mypkg.core", False)


def test_multiple_independent_roots() -> None:
    paths = [
        "src/pkga/__init__.py",
        "src/pkga/m.py",
        "tools/pkgb/__init__.py",
        "tools/pkgb/n.py",
    ]
    roots = detect_import_roots(paths)
    assert roots["src/pkga/m.py"] == "src"
    assert roots["tools/pkgb/n.py"] == "tools"


def test_orphan_module_has_bare_name() -> None:
    # fichier sans __init__.py dans son dossier → module de premier niveau
    roots = detect_import_roots(["script.py", "notes/todo.py"])
    assert roots["script.py"] == ""
    assert roots["notes/todo.py"] == "notes"  # 'notes' n'est pas un package → racine d'import
    assert module_qualname("notes/todo.py", "notes") == ("todo", False)


def test_deterministic_regardless_of_order() -> None:
    paths = _src_layout()
    assert detect_import_roots(paths) == detect_import_roots(list(reversed(paths)))


def test_src_dir_that_is_a_package_is_not_a_root() -> None:
    # cas piège : un dossier 'src' qui EST un package (a un __init__.py)
    paths = ["src/__init__.py", "src/mod.py"]
    roots = detect_import_roots(paths)
    assert roots["src/mod.py"] == ""  # 'src' est le package → pas de racine à retirer
    assert module_qualname("src/mod.py", "") == ("src.mod", False)
