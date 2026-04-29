# Python Architectural Primer — Implementation Agent

## Purpose

This primer applies when the implementation_agent is writing Python code for a Python-archetype project (`primary_language: "python"` or `archetype: "mixed"`). The primer encodes the architectural decisions that the test runner (`pytest`) and coverage tool (`coverage.py` via `pytest-cov`) require to attribute coverage correctly to the source files you author. Code that violates these patterns may produce passing tests with zero or wrong coverage.

## Architectural rules

1. **Author functions in proper packages installed editable.** The unit's code lives at `src/<pkg>/<module>.py` and the project is installed via `pip install -e .` (driven by `pyproject.toml`). WHY: coverage.py instruments package source files at import time; loose-script files run as `__main__` are attributable but with confusing names, and namespace packages without a wrapping `__init__.py` (PEP 420) can fool source detection unless explicitly listed in `.coveragerc`.

2. **Tests run in-process under pytest, not via subprocess.** The implementation must NOT use `subprocess.run`, `os.system`, `multiprocessing.Process` (without `coverage.process_startup()`), or `concurrent.futures.ProcessPoolExecutor` (without process_startup) to invoke logic that the tests are supposed to cover. WHY: coverage.py instrumentation lives in the parent Python process only; subprocesses and worker processes execute uninstrumented copies of the code, so coverage is silently lost. If you must spawn subprocesses, configure `coverage run --concurrency=multiprocessing` and call `coverage.process_startup()` from a sitecustomize.py.

3. **Use pytest fixtures for paths the implementation needs to resolve relative to test data.** If the implementation reads bundled data, expose a function that takes a path argument and let the test pass `tmp_path / "name"` or `pathlib.Path(__file__).parent / "fixtures" / "name"`. Don't hardcode `os.getcwd()`-relative paths inside the implementation. WHY: the implementation function may run under pytest, in a container, or under CI's working directory — only an explicit-path argument resolves correctly under all of them.

4. **Prefer pytest over unittest in modern code; assume `pytest-cov` for coverage.** The canonical invocation is `pytest --cov=<pkg> --cov-report=term-missing`. Author your code so it loads cleanly via normal import — don't rely on `if __name__ == "__main__":` blocks for behavior the tests need to exercise (those blocks only execute when run as a script and appear permanently uncovered).

## Anti-patterns

```python
# ANTI-PATTERN: subprocess invocation of code under test
def my_function(x: int) -> int:
    out = subprocess.run(
        ["python", "-c", f"from pkg import compute; print(compute({x}))"],
        capture_output=True, text=True,
    )
    return int(out.stdout)
```

```python
# ANTI-PATTERN: production logic locked inside __main__ — never tested
def main() -> None:
    parse_input()
    do_work()      # <- coverage will permanently flag as uncovered
    write_output()

if __name__ == "__main__":
    main()
```

## Refactor patterns

```python
# CORRECT: in-process function, package-namespaced
# File: src/mypkg/my_function.py
def my_function(x: int) -> int:
    return compute(x)
```

```python
# CORRECT: caller passes resolved path; implementation accepts a path
# File: src/mypkg/loader.py
def load_data(path: pathlib.Path) -> list[dict]:
    return list(csv.DictReader(path.open()))

# File: tests/test_loader.py
def test_loads(tmp_path):
    fixture = tmp_path / "data.csv"
    fixture.write_text("a,b\n1,2\n")
    rows = load_data(fixture)
    assert rows == [{"a": "1", "b": "2"}]
```

## Coverage caveat

If the implementation legitimately must invoke a subprocess (e.g., calling an external compiled binary), the subprocess work is OUT OF SCOPE for coverage.py. Document this in the unit contract; the coverage_review agent will not flag missing coverage for the subprocess body, but expects coverage of the wrapper that constructs the subprocess command. Tests for the wrapper should not fork another Python process to drive end-to-end behavior.
