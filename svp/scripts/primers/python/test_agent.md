# Python Architectural Primer — Test Agent

## Purpose

This primer applies when the test_agent is authoring pytest tests for a Python-archetype project (`primary_language: "python"` or `archetype: "mixed"`). The test runner is `pytest` and coverage is observed by `coverage.py` (via `pytest-cov`) against the imported package namespace. The patterns below preserve that observation chain. Tests that violate them may pass while reporting zero coverage on the function they exercised, which gets misread as "code uncovered" downstream.

## Architectural rules

1. **Tests run in-process under `pytest`.** Do not author tests that fork a separate Python process via `subprocess.run`, `os.system`, `multiprocessing.Process`, or `concurrent.futures.ProcessPoolExecutor`. WHY: coverage.py instrumentation lives in the parent Python process only. Code reached only via subprocess is silently uncovered (unless `coverage run --concurrency=multiprocessing` plus `coverage.process_startup()` is wired, which is unusual and out of scope for unit tests).

2. **Never call `os.chdir()` inside a test.** WHY: `os.chdir()` changes coverage.py's reference frame for relative paths and breaks fixture lookup. If the test must run with a different working directory, use `monkeypatch.chdir(tmp_path)` — pytest's monkeypatch fixture is properly scoped (auto-reverts at test exit) and is the canonical Python idiom for temporary cwd changes.

3. **Reach functions through the package namespace, not via dynamic `exec()` or `importlib.import_module()` of the source file.** Do not write `exec(open("src/mypkg/my_function.py").read())` at the top of a test, and do not reach a function by reading source text and compiling it. WHY: the function should be reachable via normal `from mypkg import my_function`. Dynamic exec/compile creates a synthetic compile target that coverage.py cannot attribute back to the source file — assertions run, but the original (instrumented) module shows zero coverage.

## Anti-patterns

```python
# ANTI-PATTERN: os.chdir() in a test
def test_processes_data(tmp_path):
    os.chdir(tmp_path)              # <- breaks coverage.py attribution; persists to next test
    pathlib.Path("out.csv").write_text("x,y\n")
    assert pathlib.Path("out.csv").exists()
```

```python
# ANTI-PATTERN: dynamic exec() of code under test
def test_computes_total():
    src = pathlib.Path("src/mypkg/compute_total.py").read_text()
    exec(src, globals())            # <- second copy, coverage.py sees nothing
    assert compute_total([1, 2, 3]) == 6
```

```python
# ANTI-PATTERN: subprocess invocation of the code under test
def test_runs_end_to_end():
    out = subprocess.run(
        ["python", "-c", "from mypkg import run_pipeline; run_pipeline()"],
        capture_output=True, text=True,
    )
    assert "OK" in out.stdout
```

## Refactor patterns

```python
# CORRECT: monkeypatch.chdir for scoped cwd
def test_processes_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("out.csv").write_text("x,y\n")
    assert pathlib.Path("out.csv").exists()
```

```python
# CORRECT: namespace-reached function, no exec()
from mypkg.compute_total import compute_total

def test_computes_total():
    assert compute_total([1, 2, 3]) == 6
```

```python
# CORRECT: in-process call, no subprocess
from mypkg.pipeline import run_pipeline

def test_runs_end_to_end():
    result = run_pipeline()
    assert result.status == "OK"
```

## Coverage caveat

If the implementation under test legitimately uses a subprocess (e.g., an external compiled binary), the subprocess body is OUT OF SCOPE for coverage.py by construction. Tests should exercise the wrapper that constructs the subprocess command (which IS in-process) and assert on its return value, NOT fork another Python process to drive end-to-end behavior.
