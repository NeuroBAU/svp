# Python Architectural Primer — Blueprint Author

## Purpose

This primer applies when the blueprint_author agent is authoring a blueprint for a Python-archetype project (`primary_language: "python"` or `archetype: "mixed"` with Python as a side). The primer encodes architectural decisions that downstream tooling (pytest, coverage.py, pytest-cov) requires to function correctly. Blueprints that violate these conventions produce a Stage-3 implementation that cannot pass coverage review without an architectural redo.

## Architectural rules

1. **Mandate proper Python package layout.** Every Python unit blueprint declares the unit's source as a proper package under `src/<pkg>/<module>.py` with a `pyproject.toml` at the project root and tests under `tests/`. The blueprint's file-tree annotation MUST reflect this. WHY: coverage.py understands package structure (pyproject.toml + src/ layout + editable install via `pip install -e .`); loose scripts at the project root confuse source detection and fragment coverage attribution.

2. **Mandate pytest fixtures (`tmp_path`, `tmp_path_factory`) for any contract that resolves a file path inside tests.** When a unit's contract specifies that a test reads or writes a file (fixtures, golden outputs, helper data), the path MUST be expressed via a pytest-managed fixture or `pathlib.Path(__file__).parent` for files bundled alongside the test. Hard-coded absolute paths or paths constructed via `os.getcwd()` break under CI, in containers, and across developer machines. WHY: `tmp_path` is auto-isolated per test, auto-cleaned, and works identically under every invocation mode.

## Anti-patterns

```python
# ANTI-PATTERN: loose script layout (no pyproject.toml, no src/ dir)
# my_function.py             <- at project root, not under src/<pkg>/
# tests/test_something.py    <- works, but coverage.py cannot attribute
#                                package coverage without proper packaging
```

```python
# ANTI-PATTERN: hard-coded absolute path in test fixture lookup
def test_reads_fixture():
    data = open("/Users/me/project/tests/fixtures/data.csv").read()
    assert len(data) > 0
```

## Refactor patterns

```python
# CORRECT: package layout
# src/mypkg/my_function.py
# tests/test_my_function.py
# pyproject.toml             <- declares src/ layout, editable install
# pyproject.toml installs the package via `pip install -e .`
```

```python
# CORRECT: tmp_path fixture resolves under all invocation modes
def test_reads_fixture(tmp_path):
    fixture = tmp_path / "data.csv"
    fixture.write_text("a,b\n1,2\n")
    data = fixture.read_text()
    assert "a,b" in data
```

## Coverage caveat

When the blueprint contract demands a non-package layout (rare, e.g. a one-off analysis script with no package wrapping), document the coverage trade-off explicitly: coverage.py will see only the explicitly-instrumented files, not loose scripts run as `__main__`. The default for SVP-authored Python projects is the src/ package layout with editable install. Deviations require an explicit blueprint section justifying the trade-off.
