"""
Coverage gap tests for Unit 12: Hook Configurations.

These tests fill gaps identified between the blueprint's behavioral contracts
and the existing test suite. They exercise the Python check_write_authorization
and check_svp_session functions with controlled state, validate HOOKS_JSON_CONTENT
command format, and test edge cases (path normalization, missing state file,
stage 4/5 broad access, early-stage artifact blocking, *-repo/ paths, build_env
environment files, single_unit tests/ paths).

DATA ASSUMPTIONS
================

DATA ASSUMPTION: check_write_authorization reads pipeline_state.json from the
given path and returns 0 (allow) or 2 (block) based on the two-tier
authorization model.

DATA ASSUMPTION: check_svp_session checks os.environ for the given env var name
and returns 0 if set (non-empty), 2 if not set or empty.

DATA ASSUMPTION: Pipeline state JSON follows the Unit 2 schema with fields:
stage, current_unit, debug_session (with authorized, classification, phase,
affected_units sub-fields).

DATA ASSUMPTION: Infrastructure paths (.svp/, pipeline_state.json, ledgers/,
logs/) are always writable. Project artifact paths (src/, tests/, specs/,
blueprint/, references/, *-repo/) are state-gated.

DATA ASSUMPTION: Stages 0, 1, 2, and pre_stage_3 block all project artifact
paths. Stage 3 allows only the current unit's src/unit_N/ and tests/unit_N/.
Stages 4 and 5 have broad write access to all project artifact paths.

DATA ASSUMPTION: HOOKS_JSON_CONTENT uses the Claude Code plugin hook format
where each PreToolUse entry has a "matcher" field and a "hooks" array with
entries of type {"type": "command", "command": "bash scripts/..."}.

DATA ASSUMPTION: The write_authorization.sh shell script blocks all artifact
paths when pipeline_state.json is missing, but still allows infrastructure paths.
"""

import json
import os
import subprocess
import tempfile
from unittest.mock import patch

import pytest

from svp.scripts.hook_configurations import (
    HOOKS_JSON_SCHEMA,
    SVP_ENV_VAR,
    check_write_authorization,
    check_svp_session,
)


def _get_content_constant(name: str) -> str:
    """Import a content constant from the stub."""
    import svp.scripts.hook_configurations as mod
    return getattr(mod, name)


def _make_state_file(tmpdir: str, state: dict) -> str:
    """Write a pipeline state dict to a temp JSON file, return its path."""
    path = os.path.join(tmpdir, "pipeline_state.json")
    with open(path, "w") as f:
        json.dump(state, f)
    return path


def _run_write_auth_script(file_path: str, state_dict: dict) -> tuple:
    """Run write_authorization.sh with given state, return (exit_code, stdout, stderr)."""
    content = _get_content_constant("WRITE_AUTHORIZATION_SH_CONTENT")

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, "pipeline_state.json")
        with open(state_path, "w") as f:
            json.dump(state_dict, f)

        script_path = os.path.join(tmpdir, "write_authorization.sh")
        with open(script_path, "w") as f:
            f.write(content)
        os.chmod(script_path, 0o755)

        env = os.environ.copy()
        env["SVP_PLUGIN_ACTIVE"] = "1"

        tool_input = json.dumps({
            "tool_name": "write",
            "tool_input": {"file_path": file_path}
        })

        result = subprocess.run(
            ["bash", script_path],
            capture_output=True, text=True,
            env=env,
            cwd=tmpdir,
            input=tool_input,
        )
        return result.returncode, result.stdout, result.stderr


# ===========================================================================
# Section 1: check_svp_session with controlled environment
# ===========================================================================


class TestCheckSvpSessionControlled:
    """Test check_svp_session with explicit environment control."""

    def test_returns_0_when_env_var_is_set(self):
        """check_svp_session returns 0 when the named env var is set."""
        with patch.dict(os.environ, {"SVP_PLUGIN_ACTIVE": "1"}):
            result = check_svp_session("SVP_PLUGIN_ACTIVE")
        assert result == 0, "Should return 0 (allow) when SVP_PLUGIN_ACTIVE is set"

    def test_returns_2_when_env_var_not_set(self):
        """check_svp_session returns 2 when the named env var is not set."""
        env_copy = os.environ.copy()
        env_copy.pop("SVP_PLUGIN_ACTIVE", None)
        with patch.dict(os.environ, env_copy, clear=True):
            result = check_svp_session("SVP_PLUGIN_ACTIVE")
        assert result == 2, "Should return 2 (block) when SVP_PLUGIN_ACTIVE is not set"

    def test_returns_2_when_env_var_is_empty_string(self):
        """check_svp_session returns 2 when the env var is set but empty."""
        with patch.dict(os.environ, {"SVP_PLUGIN_ACTIVE": ""}):
            result = check_svp_session("SVP_PLUGIN_ACTIVE")
        assert result == 2, "Should return 2 (block) when env var is empty string"


# ===========================================================================
# Section 2: check_write_authorization -- state-gated Python function tests
# ===========================================================================


class TestCheckWriteAuthorizationStateGated:
    """Test check_write_authorization Python function with actual state files.

    DATA ASSUMPTION: The Python function mirrors the shell script behavior:
    infrastructure paths always writable, project artifact paths gated by stage.
    """

    def test_stage0_blocks_src_path(self):
        """During stage 0, src/ paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "0", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "src/unit_1/stub.py", state_path)
        assert result == 2, "src/ should be blocked during stage 0"

    def test_stage1_blocks_tests_path(self):
        """During stage 1, tests/ paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "1", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "tests/unit_1/test_foo.py", state_path)
        assert result == 2, "tests/ should be blocked during stage 1"

    def test_stage2_blocks_specs_path(self):
        """During stage 2, specs/ paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "2", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "specs/some_spec.md", state_path)
        assert result == 2, "specs/ should be blocked during stage 2"

    def test_pre_stage_3_blocks_blueprint_path(self):
        """During pre_stage_3, blueprint/ paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "pre_stage_3", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "blueprint/unit_1.md", state_path)
        assert result == 2, "blueprint/ should be blocked during pre_stage_3"

    def test_stage3_allows_current_unit_src(self):
        """During stage 3, src/unit_N/ for the current unit should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 7, "debug_session": None
            })
            result = check_write_authorization("write", "src/unit_7/stub.py", state_path)
        assert result == 0, "src/unit_7/ should be writable during stage 3 unit 7"

    def test_stage3_allows_current_unit_tests(self):
        """During stage 3, tests/unit_N/ for the current unit should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 7, "debug_session": None
            })
            result = check_write_authorization("write", "tests/unit_7/test_impl.py", state_path)
        assert result == 0, "tests/unit_7/ should be writable during stage 3 unit 7"

    def test_stage3_blocks_other_unit_src(self):
        """During stage 3, src/unit_N/ for a different unit should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 7, "debug_session": None
            })
            result = check_write_authorization("write", "src/unit_8/stub.py", state_path)
        assert result == 2, "src/unit_8/ should be blocked during stage 3 unit 7"

    def test_stage3_blocks_other_unit_tests(self):
        """During stage 3, tests/unit_N/ for a different unit should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 7, "debug_session": None
            })
            result = check_write_authorization("write", "tests/unit_8/test_impl.py", state_path)
        assert result == 2, "tests/unit_8/ should be blocked during stage 3 unit 7"

    def test_stage3_allows_specs_path(self):
        """During stage 3, specs/ should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4, "debug_session": None
            })
            result = check_write_authorization("write", "specs/spec.md", state_path)
        assert result == 0, "specs/ should be writable during stage 3"

    def test_stage4_allows_src_path(self):
        """During stage 4 (integration), src/ paths should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "4", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "src/unit_5/impl.py", state_path)
        assert result == 0, "src/ should be writable during stage 4"

    def test_stage4_allows_tests_path(self):
        """During stage 4, tests/ paths should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "4", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "tests/unit_5/test_impl.py", state_path)
        assert result == 0, "tests/ should be writable during stage 4"

    def test_stage5_allows_src_path(self):
        """During stage 5 (assembly), src/ paths should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "5", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "src/unit_1/stub.py", state_path)
        assert result == 0, "src/ should be writable during stage 5"

    def test_stage5_allows_references_path(self):
        """During stage 5, references/ paths should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "5", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "references/ref.txt", state_path)
        assert result == 0, "references/ should be writable during stage 5"

    def test_infrastructure_always_writable_with_state(self):
        """Infrastructure paths writable even at restrictive stage 0 with a state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "0", "current_unit": None, "debug_session": None
            })
            for path in [".svp/data.txt", "pipeline_state.json", "ledgers/log.jsonl", "logs/out.log"]:
                result = check_write_authorization("write", path, state_path)
                assert result == 0, f"{path} should be writable during stage 0"


# ===========================================================================
# Section 3: check_write_authorization -- path normalization
# ===========================================================================


class TestCheckWriteAuthorizationPathNormalization:
    """Test that leading ./ is stripped from file paths."""

    def test_leading_dot_slash_normalized_for_infrastructure(self):
        """Paths with leading ./ should still be recognized as infrastructure."""
        result = check_write_authorization("write", "./.svp/test.txt", "pipeline_state.json")
        assert result == 0, "./.svp/ should be normalized to .svp/ and allowed"

    def test_leading_dot_slash_normalized_for_artifact(self):
        """Paths with leading ./ should still be subject to stage gating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "0", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "./src/unit_1/stub.py", state_path)
        assert result == 2, "./src/ should be normalized and blocked at stage 0"


# ===========================================================================
# Section 4: check_write_authorization -- missing state file
# ===========================================================================


class TestCheckWriteAuthorizationMissingState:
    """Test behavior when pipeline_state.json does not exist."""

    def test_infrastructure_allowed_without_state_file(self):
        """Infrastructure paths should be writable even without a state file."""
        result = check_write_authorization(
            "write", ".svp/test.txt", "/nonexistent/path/pipeline_state.json"
        )
        assert result == 0, ".svp/ should be writable even without state file"

    def test_artifact_blocked_without_state_file(self):
        """Artifact paths should be blocked when state file is missing."""
        result = check_write_authorization(
            "write", "src/unit_1/stub.py", "/nonexistent/path/pipeline_state.json"
        )
        assert result == 2, "Artifact paths should be blocked when state file is missing"


# ===========================================================================
# Section 5: check_write_authorization -- debug session Python function tests
# ===========================================================================


class TestCheckWriteAuthorizationDebugPython:
    """Test check_write_authorization debug session logic via Python function.

    DATA ASSUMPTION: Debug session states follow Unit 2 schema.
    """

    def test_unauthorized_debug_blocks_artifacts(self):
        """When debug_session.authorized is false, artifact writes are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "triage_readonly",
                    "authorized": False,
                }
            })
            result = check_write_authorization("write", "src/unit_4/stub.py", state_path)
        assert result == 2, "Artifacts should be blocked with unauthorized debug session"

    def test_unauthorized_debug_allows_infrastructure(self):
        """When debug_session.authorized is false, infrastructure paths are still writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "triage_readonly",
                    "authorized": False,
                }
            })
            result = check_write_authorization("write", ".svp/data.txt", state_path)
        assert result == 0, "Infrastructure should be writable with unauthorized debug"

    def test_authorized_debug_regressions_always_writable(self):
        """During authorized debug, tests/regressions/ is always writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "regression_test",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "tests/regressions/test_bug1.py", state_path)
        assert result == 0, "tests/regressions/ should always be writable during authorized debug"

    def test_authorized_build_env_allows_init_py(self):
        """During build_env debug, __init__.py should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": None,
                "debug_session": {
                    "bug_id": 2, "classification": "build_env",
                    "affected_units": [], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "src/unit_4/__init__.py", state_path)
        assert result == 0, "__init__.py should be writable during build_env debug"

    def test_authorized_build_env_blocks_impl_py(self):
        """During build_env debug, implementation .py files are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": None,
                "debug_session": {
                    "bug_id": 2, "classification": "build_env",
                    "affected_units": [], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "src/unit_4/stub.py", state_path)
        assert result == 2, "Implementation .py files should be blocked during build_env debug"

    def test_authorized_build_env_allows_pyproject_toml(self):
        """During build_env debug, pyproject.toml should be writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": None,
                "debug_session": {
                    "bug_id": 2, "classification": "build_env",
                    "affected_units": [], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "pyproject.toml", state_path)
        assert result == 0, "pyproject.toml should be writable during build_env debug"

    def test_authorized_single_unit_allows_affected_src(self):
        """During single_unit debug, src/unit_N/ for affected unit is writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "src/unit_4/impl.py", state_path)
        assert result == 0, "src/unit_4/ should be writable for affected unit"

    def test_authorized_single_unit_allows_affected_tests(self):
        """During single_unit debug, tests/unit_N/ for affected unit is writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "tests/unit_4/test_impl.py", state_path)
        assert result == 0, "tests/unit_4/ should be writable for affected unit"

    def test_authorized_single_unit_blocks_unaffected_src(self):
        """During single_unit debug, src/unit_N/ for unaffected unit is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "src/unit_5/impl.py", state_path)
        assert result == 2, "src/unit_5/ should be blocked for unaffected unit"

    def test_authorized_single_unit_blocks_unaffected_tests(self):
        """During single_unit debug, tests/unit_N/ for unaffected unit is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": "single_unit",
                    "affected_units": [4], "phase": "repair",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", "tests/unit_5/test_impl.py", state_path)
        assert result == 2, "tests/unit_5/ should be blocked for unaffected unit"

    def test_triage_allows_triage_scratch(self):
        """During triage phase, .svp/triage_scratch/ is writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": None,
                    "affected_units": [], "phase": "triage",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", ".svp/triage_scratch/notes.txt", state_path)
        assert result == 0, ".svp/triage_scratch/ should be writable during triage"

    def test_triage_readonly_allows_triage_scratch(self):
        """During triage_readonly phase, .svp/triage_scratch/ is writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4,
                "debug_session": {
                    "bug_id": 1, "classification": None,
                    "affected_units": [], "phase": "triage_readonly",
                    "authorized": True,
                }
            })
            result = check_write_authorization("write", ".svp/triage_scratch/notes.txt", state_path)
        assert result == 0, ".svp/triage_scratch/ should be writable during triage_readonly"


# ===========================================================================
# Section 6: *-repo/ paths
# ===========================================================================


class TestRepoPathHandling:
    """Test that *-repo/ project paths are state-gated.

    DATA ASSUMPTION: The blueprint lists projectname-repo/ as a state-gated
    project artifact path.
    """

    def test_repo_path_blocked_at_stage_0(self):
        """*-repo/ paths should be blocked during stage 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "0", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "myproject-repo/README.md", state_path)
        assert result == 2, "*-repo/ should be blocked during stage 0"

    def test_repo_path_allowed_at_stage_4(self):
        """*-repo/ paths should be writable during stage 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "4", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "myproject-repo/README.md", state_path)
        assert result == 0, "*-repo/ should be writable during stage 4"

    def test_repo_path_allowed_at_stage_5(self):
        """*-repo/ paths should be writable during stage 5."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "5", "current_unit": None, "debug_session": None
            })
            result = check_write_authorization("write", "myproject-repo/src/main.py", state_path)
        assert result == 0, "*-repo/ should be writable during stage 5"

    def test_repo_path_allowed_at_stage_3(self):
        """*-repo/ paths should be writable during stage 3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": 4, "debug_session": None
            })
            result = check_write_authorization("write", "myproject-repo/file.txt", state_path)
        assert result == 0, "*-repo/ should be writable during stage 3"


# ===========================================================================
# Section 7: build_env allows additional environment files
# ===========================================================================


class TestBuildEnvEnvironmentFiles:
    """Test that build_env debug classification allows additional env files.

    DATA ASSUMPTION: Blueprint says environment files, pyproject.toml, __init__.py,
    and directory structure are writable during build_env. This includes
    setup.py, setup.cfg, requirements*.txt, environment.yml, .env files.
    """

    @pytest.fixture
    def build_env_state_path(self):
        """Create a temporary directory with build_env debug state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = _make_state_file(tmpdir, {
                "stage": "3", "current_unit": None,
                "debug_session": {
                    "bug_id": 2, "classification": "build_env",
                    "affected_units": [], "phase": "repair",
                    "authorized": True,
                }
            })
            yield state_path

    def test_allows_setup_py(self, build_env_state_path):
        """setup.py should be writable during build_env debug."""
        result = check_write_authorization("write", "setup.py", build_env_state_path)
        assert result == 0, "setup.py should be writable during build_env debug"

    def test_allows_setup_cfg(self, build_env_state_path):
        """setup.cfg should be writable during build_env debug."""
        result = check_write_authorization("write", "setup.cfg", build_env_state_path)
        assert result == 0, "setup.cfg should be writable during build_env debug"

    def test_allows_requirements_txt(self, build_env_state_path):
        """requirements.txt should be writable during build_env debug."""
        result = check_write_authorization("write", "requirements.txt", build_env_state_path)
        assert result == 0, "requirements.txt should be writable during build_env debug"

    def test_allows_dot_env(self, build_env_state_path):
        """.env should be writable during build_env debug."""
        result = check_write_authorization("write", ".env", build_env_state_path)
        assert result == 0, ".env should be writable during build_env debug"


# ===========================================================================
# Section 8: HOOKS_JSON_CONTENT command type format
# ===========================================================================


class TestHooksJsonContentCommandFormat:
    """Validate HOOKS_JSON_CONTENT inner command format per blueprint.

    DATA ASSUMPTION: Each PreToolUse hook entry has a "hooks" array with entries
    of {"type": "command", "command": "bash scripts/..."}.
    """

    def test_write_hook_has_hooks_array_with_command_entries(self):
        """Write authorization hook entry must have a 'hooks' array with command type entries."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        # Find write hook
        write_hook = None
        for h in hooks_list:
            if "matcher" in h and ("write" in h["matcher"].lower() or "edit" in h["matcher"].lower()):
                write_hook = h
                break
        assert write_hook is not None, "Must have a write authorization hook"
        assert "hooks" in write_hook, "Write hook must have a 'hooks' array"
        assert isinstance(write_hook["hooks"], list), "Write hook 'hooks' must be a list"
        assert len(write_hook["hooks"]) >= 1, "Write hook 'hooks' must have at least one entry"
        cmd_entry = write_hook["hooks"][0]
        assert cmd_entry.get("type") == "command", "Hook entry type must be 'command'"
        assert "command" in cmd_entry, "Hook entry must have 'command' field"
        assert "write_authorization" in cmd_entry["command"], (
            "Command must reference write_authorization script"
        )

    def test_bash_hook_has_hooks_array_with_command_entries(self):
        """Bash (non-SVP) hook entry must have a 'hooks' array with command type entries."""
        content = _get_content_constant("HOOKS_JSON_CONTENT")
        parsed = json.loads(content)
        hooks_list = parsed["hooks"]["PreToolUse"]
        # Find bash hook
        bash_hook = None
        for h in hooks_list:
            if "matcher" in h and h["matcher"].lower() == "bash":
                bash_hook = h
                break
        assert bash_hook is not None, "Must have a bash (non-SVP) hook"
        assert "hooks" in bash_hook, "Bash hook must have a 'hooks' array"
        assert isinstance(bash_hook["hooks"], list), "Bash hook 'hooks' must be a list"
        assert len(bash_hook["hooks"]) >= 1, "Bash hook 'hooks' must have at least one entry"
        cmd_entry = bash_hook["hooks"][0]
        assert cmd_entry.get("type") == "command", "Hook entry type must be 'command'"
        assert "command" in cmd_entry, "Hook entry must have 'command' field"
        assert "non_svp_protection" in cmd_entry["command"], (
            "Command must reference non_svp_protection script"
        )


# ===========================================================================
# Section 9: Shell script execution -- early stage artifact blocking
# ===========================================================================


class TestShellScriptEarlyStageBlocking:
    """Test that the shell script blocks artifact paths during early stages.

    DATA ASSUMPTION: Stages 0, 1, 2 block all project artifact paths via shell.
    """

    def test_stage0_blocks_src_via_shell(self):
        """Shell script: stage 0 should block src/ writes."""
        state = {"stage": "0", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("src/unit_1/stub.py", state)
        assert exit_code == 2, f"src/ should be blocked at stage 0 via shell, got {exit_code}"

    def test_stage2_blocks_tests_via_shell(self):
        """Shell script: stage 2 should block tests/ writes."""
        state = {"stage": "2", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("tests/unit_1/test_foo.py", state)
        assert exit_code == 2, f"tests/ should be blocked at stage 2 via shell, got {exit_code}"

    def test_pre_stage_3_blocks_references_via_shell(self):
        """Shell script: pre_stage_3 should block references/ writes."""
        state = {"stage": "pre_stage_3", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("references/ref.txt", state)
        assert exit_code == 2, f"references/ should be blocked at pre_stage_3 via shell, got {exit_code}"


# ===========================================================================
# Section 10: Shell script execution -- stage 4/5 broad access
# ===========================================================================


class TestShellScriptBroadAccess:
    """Test that the shell script allows broad write access at stages 4 and 5.

    DATA ASSUMPTION: Stages 4 and 5 allow writes to all project artifact paths.
    """

    def test_stage4_allows_src_via_shell(self):
        """Shell script: stage 4 should allow src/ writes."""
        state = {"stage": "4", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("src/unit_5/impl.py", state)
        assert exit_code == 0, f"src/ should be allowed at stage 4, got {exit_code}"

    def test_stage4_allows_tests_via_shell(self):
        """Shell script: stage 4 should allow tests/ writes."""
        state = {"stage": "4", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("tests/unit_5/test_impl.py", state)
        assert exit_code == 0, f"tests/ should be allowed at stage 4, got {exit_code}"

    def test_stage5_allows_blueprint_via_shell(self):
        """Shell script: stage 5 should allow blueprint/ writes."""
        state = {"stage": "5", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("blueprint/unit_1.md", state)
        assert exit_code == 0, f"blueprint/ should be allowed at stage 5, got {exit_code}"

    def test_stage5_allows_references_via_shell(self):
        """Shell script: stage 5 should allow references/ writes."""
        state = {"stage": "5", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("references/ref.txt", state)
        assert exit_code == 0, f"references/ should be allowed at stage 5, got {exit_code}"


# ===========================================================================
# Section 11: Shell script -- single_unit debug tests/ paths
# ===========================================================================


class TestShellScriptSingleUnitTestsPaths:
    """Test shell script single_unit debug handling of tests/unit_N/ paths.

    DATA ASSUMPTION: During single_unit debug, tests/unit_N/ is writable only
    for affected units.
    """

    def test_single_unit_allows_affected_tests(self):
        """Shell: tests/unit_N/ for affected unit should be writable."""
        state = {
            "stage": "3", "current_unit": 4,
            "debug_session": {
                "bug_id": 1, "classification": "single_unit",
                "affected_units": [4], "phase": "repair",
                "authorized": True,
            }
        }
        exit_code, _, _ = _run_write_auth_script("tests/unit_4/test_impl.py", state)
        assert exit_code == 0, f"tests/unit_4/ should be writable for affected unit, got {exit_code}"

    def test_single_unit_blocks_unaffected_tests(self):
        """Shell: tests/unit_N/ for unaffected unit should be blocked."""
        state = {
            "stage": "3", "current_unit": 4,
            "debug_session": {
                "bug_id": 1, "classification": "single_unit",
                "affected_units": [4], "phase": "repair",
                "authorized": True,
            }
        }
        exit_code, _, _ = _run_write_auth_script("tests/unit_5/test_impl.py", state)
        assert exit_code == 2, f"tests/unit_5/ should be blocked for unaffected unit, got {exit_code}"


# ===========================================================================
# Section 12: Non-SVP protection block message directs to svp command
# ===========================================================================


class TestNonSvpProtectionMessageDirectsSvpCommand:
    """Test that non_svp_protection.sh block message directs human to use svp command.

    DATA ASSUMPTION: The blueprint says "blocks all bash commands with a message
    directing the human to use the `svp` command".
    """

    def test_block_message_mentions_svp_command(self):
        """Block message must direct the human to use the svp command."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        # The script should contain a reference to using the 'svp' command
        assert "svp" in content.lower(), (
            "Block message must mention the svp command"
        )

    def test_shell_execution_block_message_directs_to_svp(self):
        """Running the script without env var produces a message about using svp."""
        content = _get_content_constant("NON_SVP_PROTECTION_SH_CONTENT")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(content)
            f.flush()
            tmp_path = f.name
        try:
            os.chmod(tmp_path, 0o755)
            env = os.environ.copy()
            env.pop("SVP_PLUGIN_ACTIVE", None)
            result = subprocess.run(
                ["bash", tmp_path],
                capture_output=True, text=True,
                env=env,
            )
            combined = result.stdout + result.stderr
            # Must mention using the 'svp' command
            assert "'svp'" in combined or "svp" in combined.lower(), (
                f"Block message should direct human to use svp command. Output: {combined}"
            )
        finally:
            os.unlink(tmp_path)


# ===========================================================================
# Section 13: Write authorization shell script -- block message content
# ===========================================================================


class TestWriteAuthorizationBlockMessage:
    """Test that write_authorization.sh block messages explain why path is not writable.

    DATA ASSUMPTION: The blueprint says exit code 2 "blocks the write and returns
    a message explaining why the path is not writable in the current state".
    """

    def test_block_message_includes_path(self):
        """When blocking, the message should reference the blocked path."""
        state = {"stage": "0", "current_unit": None, "debug_session": None}
        exit_code, stdout, stderr = _run_write_auth_script("src/unit_1/stub.py", state)
        assert exit_code == 2
        combined = stdout + stderr
        # The message should mention the path being blocked
        assert "src/unit_1/stub.py" in combined or "src/" in combined, (
            f"Block message should reference the blocked path. Output: {combined}"
        )
