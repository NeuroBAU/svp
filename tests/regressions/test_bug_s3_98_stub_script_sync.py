"""Regression tests for Bug S3-98: Stub/script sync and import correctness.

Verifies that:
- All workspace scripts are derivable from their stubs (no content drift)
- No test file imports from src.unit_N.stub when a deployed module exists
- IMPORT_REWRITE_MAP and STUB_TO_SCRIPT are complete and valid
- Import rewriting mechanics work correctly
"""

import re
from pathlib import Path

import pytest

from derive_scripts_from_stubs import (
    IMPORT_REWRITE_MAP,
    STUB_TO_SCRIPT,
    UNIT_16_IMPORT_TO_MODULE,
    rewrite_imports,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Detect layout: workspace has scripts/, repo has svp/scripts/
_IS_WORKSPACE = (PROJECT_ROOT / "scripts").is_dir()


def _resolve_script_path(script_path: str) -> Path:
    """Resolve a STUB_TO_SCRIPT value to an actual path in either layout."""
    # STUB_TO_SCRIPT uses workspace paths: "scripts/X.py"
    if _IS_WORKSPACE:
        return PROJECT_ROOT / script_path
    # In repo: scripts/X.py -> svp/scripts/X.py
    return PROJECT_ROOT / script_path.replace("scripts/", "svp/scripts/", 1)


# Units that have NO script equivalent (agents, commands, hooks, skills, configs)
# These are allowed in test imports because they are definition-only units.
_NON_SCRIPT_UNITS = {
    "src.unit_17.stub",  # hooks
    "src.unit_18.stub",  # setup agent
    "src.unit_19.stub",  # blueprint checker
    "src.unit_20.stub",  # construction agents
    "src.unit_21.stub",  # diagnostic agents
    "src.unit_22.stub",  # support agents
    "src.unit_24.stub",  # debug agents
    "src.unit_25.stub",  # commands
    "src.unit_26.stub",  # orchestration skill
    "src.unit_27.stub",  # toolchain defaults
}


class TestStubScriptDrift:
    """Bug S3-98: Every script must be derivable from its stub."""

    @pytest.mark.parametrize(
        "stub_path,script_path",
        sorted(STUB_TO_SCRIPT.items()),
        ids=[s.split("/")[1] for s in sorted(STUB_TO_SCRIPT.keys())],
    )
    def test_script_matches_derived_stub(self, stub_path, script_path):
        """Script must equal stub with imports rewritten."""
        stub_file = PROJECT_ROOT / stub_path
        script_file = _resolve_script_path(script_path)

        assert stub_file.exists(), f"Stub not found: {stub_path}"
        assert script_file.exists(), f"Script not found: {script_file}"

        stub_content = stub_file.read_text()
        derived = rewrite_imports(stub_content)
        actual = script_file.read_text()

        assert derived == actual, (
            f"{script_file.relative_to(PROJECT_ROOT)} has drifted from {stub_path}. "
            f"Run: python3 scripts/derive_scripts_from_stubs.py && bash sync_workspace.sh"
        )


class TestRegressionTestImports:
    """Bug S3-98: No test file may import from a stub that has a deployed module."""

    def _collect_test_files(self):
        """Find all .py files under tests/."""
        test_dir = PROJECT_ROOT / "tests"
        return sorted(test_dir.rglob("*.py"))

    def _find_stub_imports(self, filepath):
        """Find all 'from src.unit_N.stub import' lines that should use deployed modules."""
        violations = []
        content = filepath.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            match = re.match(r"^\s*from (src\.unit_\d+\.stub) import", line)
            if match:
                stub_path = match.group(1)
                if stub_path in _NON_SCRIPT_UNITS:
                    continue  # allowed
                module = IMPORT_REWRITE_MAP.get(stub_path)
                if module:
                    violations.append(
                        f"  Line {i}: {line.strip()}\n"
                        f"    -> should be: from {module} import ..."
                    )
        return violations

    def test_no_stub_imports_in_tests(self):
        """All test files must import from deployed modules, not stubs."""
        all_violations = {}
        for test_file in self._collect_test_files():
            violations = self._find_stub_imports(test_file)
            if violations:
                rel = test_file.relative_to(PROJECT_ROOT)
                all_violations[str(rel)] = violations

        if all_violations:
            msg = "Test files importing from stubs instead of deployed modules:\n"
            for filepath, viols in sorted(all_violations.items()):
                msg += f"\n{filepath}:\n" + "\n".join(viols) + "\n"
            pytest.fail(msg)


class TestImportRewriteMapCompleteness:
    """Bug S3-98: IMPORT_REWRITE_MAP and STUB_TO_SCRIPT must be complete."""

    def test_every_stub_in_map_exists(self):
        """Every stub file referenced in STUB_TO_SCRIPT must exist."""
        for stub_path in STUB_TO_SCRIPT:
            assert (PROJECT_ROOT / stub_path).exists(), f"Stub missing: {stub_path}"

    def test_every_script_in_map_exists(self):
        """Every script file referenced in STUB_TO_SCRIPT must exist."""
        for script_path in STUB_TO_SCRIPT.values():
            resolved = _resolve_script_path(script_path)
            assert resolved.exists(), f"Script missing: {resolved}"

    def test_rewrite_map_covers_all_stubs(self):
        """Every stub in STUB_TO_SCRIPT must have a rewrite map entry."""
        for stub_path in STUB_TO_SCRIPT:
            # Extract the import path: src/unit_N/stub.py -> src.unit_N.stub
            parts = stub_path.replace("/", ".").replace(".py", "")
            assert parts in IMPORT_REWRITE_MAP or parts == "src.unit_16.stub", (
                f"IMPORT_REWRITE_MAP missing entry for {parts}"
            )


class TestDerivationMechanics:
    """Bug S3-98: Import rewriting must transform correctly."""

    def test_standard_import_rewrite(self):
        """from src.unit_5.stub import X -> from pipeline_state import X."""
        line = "from src.unit_5.stub import PipelineState, load_state"
        result = rewrite_imports(line)
        assert result == "from pipeline_state import PipelineState, load_state"

    def test_indented_import_rewrite(self):
        """Indented imports inside functions are also rewritten."""
        line = "    from src.unit_3.stub import load_profile"
        result = rewrite_imports(line)
        assert result == "    from profile_schema import load_profile"

    def test_unit_16_context_dependent(self):
        """Unit 16 imports route to correct module based on imported name."""
        line = "from src.unit_16.stub import sync_pass1_artifacts"
        result = rewrite_imports(line)
        assert result == "from sync_debug_docs import sync_pass1_artifacts"

    def test_non_import_lines_unchanged(self):
        """Lines that aren't imports pass through unchanged."""
        line = "x = src.unit_5.stub.PipelineState()"
        result = rewrite_imports(line)
        assert result == line

    def test_non_script_unit_unchanged(self):
        """Units without script equivalents (17-27) are not rewritten."""
        line = "from src.unit_17.stub import generate_hooks_json"
        result = rewrite_imports(line)
        assert result == line  # no rewrite — unit 17 has no script

    def test_multiline_content(self):
        """Full file content with multiple imports is rewritten correctly."""
        content = (
            "from src.unit_1.stub import ARTIFACT_FILENAMES\n"
            "from src.unit_5.stub import PipelineState\n"
            "\n"
            "def foo():\n"
            "    state = PipelineState()\n"
        )
        result = rewrite_imports(content)
        assert "from svp_config import ARTIFACT_FILENAMES" in result
        assert "from pipeline_state import PipelineState" in result
        assert "    state = PipelineState()" in result
