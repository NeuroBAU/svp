# Python Architectural Primer — Coverage Review

## Purpose

This primer applies when the coverage_review agent is reviewing coverage.py reports for a Python-archetype project (`primary_language: "python"` or `archetype: "mixed"`). The most common review-time error is to read low coverage as "missing tests" when in fact coverage.py lost the attribution due to an architectural pattern in the test or the code. Adding more tests will not fix attribution-loss; only refactoring will. The patterns below let you distinguish "code is uncovered" from "coverage.py lost the trace."

## Architectural rules

1. **Recognize the five coverage.py attribution-loss vectors.** When coverage is unexpectedly low for a function that has tests targeting it, check for these patterns BEFORE concluding tests are missing:
   - **(a) `os.chdir()` inside a test** — wd-dependent paths confuse coverage.py's source-file map and persist into the next test.
   - **(b) Dynamic `exec()`, `compile()`, or `importlib.import_module()` of source text** — coverage.py sees a synthetic compile target, not the source file; assertions run against the synthetic copy.
   - **(c) Subprocess invocations** (`subprocess.run`, `os.system`, `subprocess.Popen`) — coverage.py instrumentation lives in the parent Python process only; child-process code runs uninstrumented unless `coverage run --concurrency=multiprocessing` plus `coverage.process_startup()` is wired.
   - **(d) `if __name__ == "__main__":` blocks** — only exercised when run as a script; never exercised when imported by tests; appear permanently uncovered.
   - **(e) Multiprocessing workers** (`multiprocessing.Process`, `multiprocessing.Pool`, `concurrent.futures.ProcessPoolExecutor`) without `coverage.process_startup()` — workers run uninstrumented copies. (Note: `ThreadPoolExecutor` is usually fine because threads share the parent process.)
   WHY: each vector silently moves execution to code that coverage.py did not (or cannot) instrument.

2. **Refuse coverage-aware special branches as a fix for low coverage.** If you see a PR adding `if "coverage" in sys.modules: ...` (or any equivalent runtime check for coverage's presence) to make coverage numbers go up, REJECT it. WHY: that hack hides the architectural cause (one of the five vectors above). Find and fix the architectural cause; don't paint over the symptom.

3. **Coverage is signal, not goal.** Low coverage often signals a test-architecture problem, not a missing test. Diagnose first; require additional tests only after the five vectors are ruled out. WHY: adding tests on top of a broken attribution chain produces "more tests, same coverage number" — wasted effort and a false sense that the codebase is hard to test.

4. **Know the coverage.py quirks that produce confusing reports.** Even with clean tests:
   - `pytest-xdist` parallel tests (`pytest -n 4`) need `--cov-context=test` (or context-tracking config) for correct attribution; without it, contexts collide and the resulting report under-counts.
   - Namespace packages (PEP 420 — directories without `__init__.py`) can fool coverage.py's source detection. Use a `.coveragerc` with explicit `source =` or `include =` lists, or restore `__init__.py`.
   - Jupyter notebook execution is opaque to coverage.py — measuring coverage of code that runs only in a notebook will not work.
   - `ProcessPoolExecutor` requires `coverage.process_startup()` registration via a `sitecustomize.py` or pytest plugin (`pytest-cov` ships one). `ThreadPoolExecutor` is usually fine.
   When the report's numbers depend on the invocation environment, the project's coverage.py setup itself is suspect — flag it as a separate finding.

## Anti-patterns to flag in review

```python
# FLAG: coverage-aware special branch (rule 2)
def my_function(x):
    if "coverage" in sys.modules:
        return 42                   # <- coverage hack, REJECT
    # ...real implementation...
```

```python
# FLAG: dynamic exec() inside a test (rule 1b)
def test_works():
    exec(pathlib.Path("src/mypkg/my_function.py").read_text(), globals())
    assert my_function(1) == 1
```

```python
# FLAG: subprocess invocation in a test (rule 1c)
def test_end_to_end():
    out = subprocess.run(
        ["python", "-c", "from mypkg import run; run()"],
        capture_output=True, text=True,
    )
    assert "OK" in out.stdout
```

## Refactor recommendations to issue

When a finding cites one of the five attribution-loss vectors, the recommendation should be to refactor the test or the implementation to eliminate the vector — NOT to add more tests, NOT to add `# pragma: no cover` comments wholesale, NOT to add `if "coverage" in sys.modules:` branches. Cite the rule from the test_agent or implementation_agent primer that the project's Python code violates.

## Coverage caveat

A function with legitimately uncoverable bodies (e.g., wrapping an external subprocess) should be documented in the unit's blueprint contract with an explicit "coverage scope" note, ideally combined with a targeted `# pragma: no cover` only on the unreachable line. The coverage_review's job is to verify the wrapper itself is covered, not to chase the subprocess body. When you see such a function and the wrapper is fully tested, accept the coverage profile.
