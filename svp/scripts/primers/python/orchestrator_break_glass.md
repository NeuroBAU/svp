# Python Architectural Primer — Orchestrator Break-Glass

## Purpose

This primer applies when the orchestrator (main session) enters break-glass mode on a Python-archetype child project (`primary_language: "python"` or `archetype: "mixed"`). It is the diagnostic-flavored subset of the Python coverage-architecture knowledge: enough to recognize the attribution-loss patterns when triaging a coverage.py report or a flaky test, without the full anti-pattern catalog the test_agent and implementation_agent carry. Use this primer to diagnose; delegate the fix to the appropriate agent.

## Diagnostic rules

1. **Before adding tests, confirm coverage.py's attribution chain is intact.** When a coverage.py report shows surprisingly low coverage on a function that has tests, five vectors silently break attribution:
   - **(a) `os.chdir()` inside a test** — coverage.py's source-file map gets confused; effects persist into the next test.
   - **(b) Dynamic `exec()`/`compile()`/`importlib.import_module()` of source text** — coverage.py sees a synthetic compile target, not the real source file; assertions hit the second copy.
   - **(c) Subprocess invocation** (`subprocess.run`, `os.system`, `subprocess.Popen`) — coverage.py instruments only the parent Python process.
   - **(d) `if __name__ == "__main__":` blocks** — only exercised when run as a script; tests that import the module never reach them; permanent uncoverable artifact.
   - **(e) Multiprocessing workers** (`multiprocessing.Process`, `Pool`, `ProcessPoolExecutor`) without `coverage.process_startup()` — workers run uninstrumented.
   When triaging, grep the test files and the implementation for `os.chdir`, `exec(`, `compile(`, `importlib.import_module`, `subprocess.run`, `os.system`, `multiprocessing.`, `ProcessPoolExecutor`, and the `if __name__ == "__main__"` idiom BEFORE asking the test_agent for more coverage.

2. **Reject coverage-aware special branches as a fix.** If diagnosis surfaces `if "coverage" in sys.modules: ...` (or any equivalent runtime check for coverage's presence) in implementation code, do NOT pass them through. They hide architectural bugs from rule 1. Open a bug to refactor the underlying test or implementation; cite the relevant rule from the test_agent or implementation_agent primer.

3. **Coverage is signal, not goal — diagnose before adding tests.** Resist the urge to "just write more tests" when a coverage.py number looks low. A low number often signals a coverage attribution-chain break (rule 1) — adding tests on top will not raise the number, and you will diagnose the symptom twice. Do the architectural diagnosis first; route the fix to test_agent or implementation_agent based on which side carries the violation.

## Diagnostic workflow

```
coverage.py report shows low coverage on <function>
   |
   v
Step 1: grep tests/ + src/ for the five attribution-loss vectors
   - os.chdir, exec(, compile(, importlib.import_module
   - subprocess.run, os.system, subprocess.Popen
   - multiprocessing., ProcessPoolExecutor
   - if __name__ == "__main__":
   |
   +---- match found ----> Architectural cause. Route to test_agent (test side) or
   |                       implementation_agent (impl side) for refactor.
   |                       Do NOT add tests.
   |
   v
Step 2: confirm tests reach the function via package namespace
   - is the function importable as `from mypkg import fn`?
   - is `pip install -e .` in effect (editable install)?
   |
   +---- not reachable ----> blueprint_author / implementation_agent issue.
   |                         Function should be authored under src/<pkg>/.
   |
   v
Step 3: only after steps 1-2 rule out attribution-loss and reachability,
        consider that tests are genuinely missing. Route to test_agent.
```

## What to delegate, not solve in-place

The orchestrator's role in break-glass on a Python project is to recognize the architectural pattern and dispatch the fix to the correct subagent. Do NOT edit Python source files in-place to silence a coverage.py report. Do NOT add `# pragma: no cover` wholesale. Do route a finding like "test file `tests/test_foo.py` calls `os.chdir()` at line 12; refactor to `monkeypatch.chdir(tmp_path)`" to the test_agent and let it carry the fix through the unit's normal cycle.

## When the report itself is suspect

If the same coverage.py invocation produces different numbers on different machines (`pytest --cov` vs `coverage run -m pytest`), or `pytest-xdist` parallel runs disagree with serial runs, the project's coverage setup is itself the bug — flag it as a separate finding rather than treating either number as ground truth. Cite the coverage_review primer rule on coverage.py quirks (`pytest-xdist` context tracking, namespace packages, `ProcessPoolExecutor` startup) for the contributor reading the bug entry.
