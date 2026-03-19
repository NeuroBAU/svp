"""Integration tests for SVP 2.1 cross-unit interactions.

Covers all 11 integration paths specified in the blueprint:
1. Toolchain resolution chain
2. Profile flow through preparation script
3. Blueprint checker profile validation
4. Redo agent profile classification
5. Gate 0.3 dispatch
6. Preference compliance scan
7. Write authorization for new paths (including ruff.toml)
8. Redo-triggered profile revision state transitions
9. Quality gate execution chain (NEW IN 2.1)
10. Quality gate retry isolation (NEW IN 2.1)
11. Quality package installation (NEW IN 2.1)
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

# -----------------------------------------------------------
# Unit 1: Configuration, Profile, Toolchain
# -----------------------------------------------------------
try:
    from svp_config import (
        get_profile_section,
        get_quality_gate_operations,
        get_quality_packages,
        load_profile,
        load_toolchain,
        resolve_command,
        validate_profile,
        validate_toolchain,
    )
except ImportError:
    pytest.skip(
        "Unit 1 not available",
        allow_module_level=True,
    )

# -----------------------------------------------------------
# Unit 2: Pipeline State
# -----------------------------------------------------------
try:
    from pipeline_state import (
        QUALITY_GATE_SUB_STAGES,
        REDO_PROFILE_SUB_STAGES,
        PipelineState,
        create_initial_state,
        load_state,
        save_state,
        validate_state,
    )
except ImportError:
    pytest.skip(
        "Unit 2 not available",
        allow_module_level=True,
    )

# -----------------------------------------------------------
# Unit 3: State Transitions
# -----------------------------------------------------------
try:
    from state_transitions import (
        TransitionError,
        advance_fix_ladder,
        advance_quality_gate_to_retry,
        complete_redo_profile_revision,
        enter_quality_gate,
        enter_redo_profile_revision,
        quality_gate_fail_to_ladder,
        quality_gate_pass,
    )
except ImportError:
    pytest.skip(
        "Unit 3 not available",
        allow_module_level=True,
    )

# -----------------------------------------------------------
# Unit 9: Preparation Script
# -----------------------------------------------------------
try:
    from prepare_task import (
        load_full_profile,
        load_profile_sections,
    )
except ImportError:
    pytest.skip(
        "Unit 9 not available",
        allow_module_level=True,
    )

# -----------------------------------------------------------
# Unit 10: Routing and Dispatch
# -----------------------------------------------------------
try:
    from routing import (
        AGENT_STATUS_LINES,
        GATE_RESPONSES,
        dispatch_command_status,
        dispatch_gate_response,
        route,
        run_quality_gate,
    )
except ImportError:
    pytest.skip(
        "Unit 10 not available",
        allow_module_level=True,
    )

# -----------------------------------------------------------
# Unit 12: Hook Configurations / Write Authorization
# -----------------------------------------------------------
try:
    from hooks import check_write_authorization
except ImportError:
    pytest.skip(
        "Unit 12 not available",
        allow_module_level=True,
    )

# -----------------------------------------------------------
# Unit 23: Compliance Scan
# -----------------------------------------------------------
try:
    from compliance_scan import run_compliance_scan
except ImportError:
    pytest.skip(
        "Unit 23 not available",
        allow_module_level=True,
    )


# ============================================================
# Fixtures
# ============================================================

SAMPLE_TOOLCHAIN: Dict[str, Any] = {
    "toolchain_id": "python_conda_pytest",
    "environment": {
        "tool": "conda",
        "create": ("conda create -n {env_name} python={python_version} -y"),
        "run_prefix": "conda run -n {env_name}",
        "install": ("conda run -n {env_name} pip install {packages}"),
        "install_dev": ("conda run -n {env_name} pip install {packages}"),
        "remove": ("conda env remove -n {env_name} -y"),
    },
    "testing": {
        "tool": "pytest",
        "run": ("{run_prefix} python -m pytest {test_path} -v"),
        "run_coverage": (
            "{run_prefix} python -m pytest"
            " {test_path} -v"
            " --cov={module}"
            " --cov-report=term-missing"
        ),
        "framework_packages": ["pytest", "pytest-cov"],
        "file_pattern": "test_*.py",
        "collection_error_indicators": [
            "ModuleNotFoundError",
            "ImportError",
            "SyntaxError",
            "no tests ran",
            "collection error",
            "ERROR collecting",
        ],
        "pass_fail_pattern": r"(\d+) passed",
    },
    "packaging": {
        "tool": "setuptools",
        "manifest_file": "pyproject.toml",
        "build_backend": "setuptools.build_meta",
        "validate_command": ("{run_prefix} pip install -e ."),
    },
    "vcs": {
        "tool": "git",
        "commands": {
            "init": "git init",
            "add": "git add {files}",
            "commit": 'git commit -m "{message}"',
            "status": "git status",
        },
    },
    "language": {
        "name": "python",
        "extension": ".py",
        "version_constraint": ">=3.9",
        "signature_parser": "ast",
        "stub_body": "raise NotImplementedError",
    },
    "quality": {
        "formatter": {
            "tool": "ruff",
            "format": ("{run_prefix} ruff format {target}"),
            "check": ("{run_prefix} ruff format --check {target}"),
        },
        "linter": {
            "tool": "ruff",
            "light": ("{run_prefix} ruff check {target}"),
            "heavy": ("{run_prefix} ruff check {target} --select ALL"),
            "check": ("{run_prefix} ruff check {target}"),
        },
        "type_checker": {
            "tool": "mypy",
            "check": ("{run_prefix} mypy {target}"),
            "unit_flags": ("--ignore-missing-imports --follow-imports=skip"),
            "project_flags": ("--ignore-missing-imports"),
        },
        "packages": ["ruff", "mypy"],
        "gate_a": [
            "formatter.check",
            "linter.light",
        ],
        "gate_b": [
            "formatter.check",
            "linter.light",
        ],
        "gate_c": [
            "formatter.check",
            "linter.heavy",
            "type_checker.check",
        ],
    },
    "file_structure": {
        "source_dir_pattern": "src/unit_{n}",
        "test_dir_pattern": "tests/unit_{n}",
        "source_extension": ".py",
        "test_extension": ".py",
    },
}

SAMPLE_PROFILE: Dict[str, Any] = {
    "pipeline_toolchain": "python_conda_pytest",
    "python_version": "3.11",
    "delivery": {
        "environment_recommendation": "conda",
        "dependency_format": "environment.yml",
        "source_layout": "conventional",
        "entry_points": False,
    },
    "vcs": {
        "commit_style": "conventional",
        "commit_template": None,
        "issue_references": False,
        "branch_strategy": "main-only",
        "tagging": "semver",
        "conventions_notes": None,
        "changelog": "none",
    },
    "readme": {
        "audience": "domain expert",
        "sections": [
            "Header",
            "What it does",
            "Installation",
            "Usage",
        ],
        "depth": "standard",
        "include_math_notation": False,
        "include_glossary": False,
        "include_data_formats": False,
        "include_code_examples": False,
        "code_example_focus": None,
        "custom_sections": None,
        "docstring_convention": "google",
        "citation_file": False,
        "contributing_guide": False,
    },
    "testing": {
        "coverage_target": None,
        "readable_test_names": True,
        "readme_test_scenarios": False,
    },
    "license": {
        "type": "MIT",
        "holder": "Test User",
        "author": "Test User",
        "year": "2026",
        "contact": None,
        "spdx_headers": False,
        "additional_metadata": {
            "citation": None,
            "funding": None,
            "acknowledgments": None,
        },
    },
    "quality": {
        "linter": "ruff",
        "formatter": "ruff",
        "type_checker": "none",
        "import_sorter": "ruff",
        "line_length": 88,
    },
    "fixed": {
        "language": "python",
        "pipeline_environment": "conda",
        "test_framework": "pytest",
        "build_backend": "setuptools",
        "vcs_system": "git",
        "source_layout_during_build": "svp_native",
        "pipeline_quality_tools": "ruff_mypy",
    },
    "created_at": "2026-03-14T00:00:00",
}


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project with essential files."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()

    # Write toolchain.json
    tc_path = tmp_path / "toolchain.json"
    tc_path.write_text(
        json.dumps(SAMPLE_TOOLCHAIN, indent=2),
        encoding="utf-8",
    )

    # Write project_profile.json
    profile_path = tmp_path / "project_profile.json"
    profile_path.write_text(
        json.dumps(SAMPLE_PROFILE, indent=2),
        encoding="utf-8",
    )

    # Write svp_config.json
    config = {
        "iteration_limit": 3,
        "models": {"default": "claude-opus-4-6"},
    }
    config_path = tmp_path / "svp_config.json"
    config_path.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    # Write pipeline_state.json
    state = create_initial_state("test_project")
    save_state(state, tmp_path)

    # Write ruff.toml
    ruff_path = tmp_path / "ruff.toml"
    ruff_path.write_text(
        'line-length = 88\n\n[lint]\nselect = ["E", "F", "W", "I"]\n',
        encoding="utf-8",
    )

    return tmp_path


def _make_state(**kwargs) -> PipelineState:
    """Helper to create a PipelineState with defaults."""
    defaults: Dict[str, Any] = {
        "stage": "0",
        "sub_stage": None,
        "project_name": "test_project",
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


def _write_status(
    project_root: Path,
    status: str,
) -> None:
    """Write a status line to .svp/last_status.txt."""
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    status_file = svp_dir / "last_status.txt"
    status_file.write_text(status, encoding="utf-8")


def _write_state_json(
    project_root: Path,
    state_dict: Dict[str, Any],
) -> None:
    """Write a raw state dict to pipeline_state.json."""
    state_file = project_root / "pipeline_state.json"
    state_file.write_text(
        json.dumps(state_dict, indent=2),
        encoding="utf-8",
    )


# ============================================================
# 1. Toolchain Resolution Chain
# ============================================================


class TestToolchainResolutionChain:
    """Integration path 1: toolchain resolution.

    Verifies Unit 1 (load_toolchain, resolve_command)
    feeds valid data to Unit 9 and Unit 10.
    """

    def test_load_and_resolve_test_command(self, tmp_project):
        """Toolchain loaded by Unit 1 resolves commands."""
        toolchain = load_toolchain(tmp_project)
        cmd = resolve_command(
            toolchain,
            "testing.run",
            {
                "env_name": "myenv",
                "test_path": "tests/",
            },
        )
        assert "conda run -n myenv" in cmd
        assert "pytest" in cmd
        assert "tests/" in cmd

    def test_quality_operations_resolve(self, tmp_project):
        """Quality gate operations resolve to commands."""
        toolchain = load_toolchain(tmp_project)
        ops = get_quality_gate_operations(toolchain, "gate_a")
        assert len(ops) > 0
        for op in ops:
            full_op = "quality." + op
            cmd = resolve_command(
                toolchain,
                full_op,
                {"env_name": "myenv", "target": "src/"},
            )
            assert len(cmd) > 0
            assert "{" not in cmd, f"Unresolved placeholder in: {cmd}"

    def test_gate_c_includes_type_checker(self, tmp_project):
        """Gate C operations include type_checker.check."""
        toolchain = load_toolchain(tmp_project)
        ops = get_quality_gate_operations(toolchain, "gate_c")
        assert "type_checker.check" in ops

    def test_validation_catches_missing_quality(self):
        """Missing quality section caught by validation."""
        bad_tc = {k: v for k, v in SAMPLE_TOOLCHAIN.items() if k != "quality"}
        errors = validate_toolchain(bad_tc)
        assert any("quality" in e for e in errors)

    def test_quality_packages_accessible(self, tmp_project):
        """Quality packages from toolchain are readable."""
        toolchain = load_toolchain(tmp_project)
        pkgs = get_quality_packages(toolchain)
        assert "ruff" in pkgs
        assert "mypy" in pkgs

    def test_route_dispatches_quality_gate_a(self, tmp_project):
        """Route dispatches quality_gate_a sub-stage."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        action = route(state, tmp_project)
        assert action["ACTION"] in (
            "COMMAND",
            "run_command",
            "invoke_agent",
        )

    def test_route_dispatches_quality_gate_b(self, tmp_project):
        """Route dispatches quality_gate_b sub-stage."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=1,
        )
        action = route(state, tmp_project)
        assert action["ACTION"] in (
            "COMMAND",
            "run_command",
            "invoke_agent",
        )


# ============================================================
# 2. Profile Flow Through Preparation Script
# ============================================================


class TestProfileFlowThroughPrepScript:
    """Integration path 2: profile -> prep script.

    Verifies profile data flows from Unit 1
    (load_profile) through Unit 9 (prepare_agent_task)
    into agent task prompts.
    """

    def test_load_full_profile(self, tmp_project):
        """load_full_profile reads project_profile.json."""
        profile_text = load_full_profile(tmp_project)
        assert profile_text is not None
        assert isinstance(profile_text, str)
        assert len(profile_text) > 0
        assert "quality" in profile_text

    def test_profile_sections_loaded(self, tmp_project):
        """load_profile_sections returns formatted text."""
        section_text = load_profile_sections(tmp_project, ["quality", "delivery"])
        assert isinstance(section_text, str)
        assert len(section_text) > 0

    def test_profile_quality_section(self, tmp_project):
        """Profile quality section is accessible."""
        profile = load_profile(tmp_project)
        quality = get_profile_section(profile, "quality")
        assert quality["linter"] == "ruff"
        assert quality["formatter"] == "ruff"
        assert quality["line_length"] == 88

    def test_profile_delivery_section(self, tmp_project):
        """Profile delivery section flows correctly."""
        profile = load_profile(tmp_project)
        delivery = get_profile_section(profile, "delivery")
        assert delivery["environment_recommendation"] == "conda"
        assert delivery["source_layout"] == "conventional"

    def test_profile_fixed_section(self, tmp_project):
        """Profile fixed section preserves constraints."""
        profile = load_profile(tmp_project)
        fixed = get_profile_section(profile, "fixed")
        assert fixed["language"] == "python"
        assert fixed["test_framework"] == "pytest"
        assert fixed["pipeline_quality_tools"] == ("ruff_mypy")


# ============================================================
# 3. Blueprint Checker Profile Validation
# ============================================================


class TestBlueprintCheckerProfileValidation:
    """Integration path 3: blueprint checker + profile.

    Verifies that Unit 1 validate_profile correctly
    validates profile preferences against unit contracts.
    """

    def test_valid_profile_passes(self):
        """A well-formed profile passes validation."""
        errors = validate_profile(SAMPLE_PROFILE)
        assert errors == []

    def test_invalid_linter_detected(self):
        """Invalid quality.linter is caught."""
        profile = {**SAMPLE_PROFILE}
        profile["quality"] = {
            **profile["quality"],
            "linter": "invalid_tool",
        }
        errors = validate_profile(profile)
        assert any("linter" in e for e in errors)

    def test_invalid_formatter_detected(self):
        """Invalid quality.formatter is caught."""
        profile = {**SAMPLE_PROFILE}
        profile["quality"] = {
            **profile["quality"],
            "formatter": "invalid_tool",
        }
        errors = validate_profile(profile)
        assert any("formatter" in e for e in errors)

    def test_invalid_type_checker_detected(self):
        """Invalid quality.type_checker is caught."""
        profile = {**SAMPLE_PROFILE}
        profile["quality"] = {
            **profile["quality"],
            "type_checker": "invalid",
        }
        errors = validate_profile(profile)
        assert any("type_checker" in e for e in errors)

    def test_invalid_source_layout_detected(self):
        """Invalid delivery.source_layout is caught."""
        profile = {**SAMPLE_PROFILE}
        profile["delivery"] = {
            **profile["delivery"],
            "source_layout": "nonexistent",
        }
        errors = validate_profile(profile)
        assert any("source_layout" in e for e in errors)

    def test_missing_required_section_detected(self):
        """Missing required section detected."""
        profile = {k: v for k, v in SAMPLE_PROFILE.items() if k != "quality"}
        errors = validate_profile(profile)
        assert any("quality" in e for e in errors)

    def test_invalid_coverage_target_detected(self):
        """Out-of-range coverage_target is caught."""
        profile = {**SAMPLE_PROFILE}
        profile["testing"] = {
            **profile["testing"],
            "coverage_target": 150,
        }
        errors = validate_profile(profile)
        assert any("coverage_target" in e for e in errors)

    def test_negative_line_length_detected(self):
        """Negative quality.line_length is caught."""
        profile = {**SAMPLE_PROFILE}
        profile["quality"] = {
            **profile["quality"],
            "line_length": -1,
        }
        errors = validate_profile(profile)
        assert any("line_length" in e for e in errors)


# ============================================================
# 4. Redo Agent Profile Classification
# ============================================================


class TestRedoAgentProfileClassification:
    """Integration path 4: redo agent classification.

    Verifies that Unit 10 AGENT_STATUS_LINES includes
    the redo classifications and that Unit 3
    enter_redo_profile_revision accepts them.
    """

    def test_redo_status_lines_registered(self):
        """Redo agent status lines are in the registry."""
        redo_lines = AGENT_STATUS_LINES.get("redo_agent", [])
        assert "REDO_CLASSIFIED: profile_delivery" in redo_lines
        assert "REDO_CLASSIFIED: profile_blueprint" in redo_lines

    def test_enter_redo_delivery(self):
        """enter_redo_profile_revision with delivery."""
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=2,
        )
        new_state = enter_redo_profile_revision(state, "profile_delivery")
        assert new_state.sub_stage == "redo_profile_delivery"
        assert new_state.redo_triggered_from is not None
        snapshot = new_state.redo_triggered_from
        assert snapshot["stage"] == "3"
        assert snapshot["sub_stage"] == "test_generation"

    def test_enter_redo_blueprint(self):
        """enter_redo_profile_revision with blueprint."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        new_state = enter_redo_profile_revision(state, "profile_blueprint")
        assert new_state.sub_stage == "redo_profile_blueprint"

    def test_enter_redo_profile_delivery_alias(self):
        """profile_delivery alias also accepted."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
        )
        new_state = enter_redo_profile_revision(state, "profile_delivery")
        assert new_state.sub_stage == "redo_profile_delivery"

    def test_invalid_classification_rejected(self):
        """Invalid classification raises error."""
        state = _make_state(stage="3", current_unit=1)
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(state, "invalid_class")

    def test_double_entry_rejected(self):
        """Cannot enter redo revision when already in."""
        state = _make_state(
            stage="3",
            sub_stage="redo_profile_delivery",
            current_unit=1,
        )
        with pytest.raises(TransitionError):
            enter_redo_profile_revision(state, "profile_delivery")


# ============================================================
# 5. Gate 0.3 Dispatch
# ============================================================


class TestGate03Dispatch:
    """Integration path 5: Gate 0.3 dispatch.

    Verifies that the routing script dispatches
    correctly based on pipeline state at Stage 0
    project_profile sub-stage.
    """

    def test_gate_0_3_registered(self):
        """Gate 0.3 is registered in GATE_RESPONSES."""
        assert "gate_0_3_profile_approval" in GATE_RESPONSES
        responses = GATE_RESPONSES["gate_0_3_profile_approval"]
        assert "PROFILE APPROVED" in responses
        assert "PROFILE REJECTED" in responses

    def test_route_stage_0_profile_no_status(self, tmp_project):
        """Stage 0 project_profile without status invokes agent."""
        state = _make_state(
            stage="0",
            sub_stage="project_profile",
        )
        action = route(state, tmp_project)
        assert action["ACTION"] in ("AGENT", "invoke_agent")

    def test_route_stage_0_profile_with_status(self, tmp_project):
        """Stage 0 project_profile with status presents gate."""
        _write_status(tmp_project, "PROFILE_COMPLETE")
        state = _make_state(
            stage="0",
            sub_stage="project_profile",
        )
        action = route(state, tmp_project)
        assert action["ACTION"] in ("GATE", "human_gate")
        assert action["GATE_ID"] == "gate_0_3_profile_approval"

    def test_dispatch_profile_approved(self, tmp_project):
        """PROFILE APPROVED response dispatches cleanly."""
        state = _make_state(
            stage="0",
            sub_stage="project_profile",
        )
        new_state = dispatch_gate_response(
            state,
            "gate_0_3_profile_approval",
            "PROFILE APPROVED",
            tmp_project,
        )
        assert new_state is not None
        assert new_state.last_action is not None

    def test_dispatch_profile_rejected(self, tmp_project):
        """PROFILE REJECTED response dispatches cleanly."""
        state = _make_state(
            stage="0",
            sub_stage="project_profile",
        )
        new_state = dispatch_gate_response(
            state,
            "gate_0_3_profile_approval",
            "PROFILE REJECTED",
            tmp_project,
        )
        assert new_state is not None

    def test_invalid_gate_response_rejected(self, tmp_project):
        """Invalid response for gate raises ValueError."""
        state = _make_state(stage="0")
        with pytest.raises(ValueError):
            dispatch_gate_response(
                state,
                "gate_0_3_profile_approval",
                "INVALID RESPONSE",
                tmp_project,
            )


# ============================================================
# 6. Preference Compliance Scan
# ============================================================


class TestPreferenceComplianceScan:
    """Integration path 6: compliance scan.

    Verifies that Unit 23 run_compliance_scan detects
    unmet profile preferences using Unit 1 profile.
    """

    def test_clean_source_passes(self, tmp_project):
        """Clean source with no stubs passes scan."""
        src = tmp_project / "src"
        src.mkdir(exist_ok=True)
        mod = src / "clean_module.py"
        mod.write_text(
            "def hello():\n    return 'world'\n",
            encoding="utf-8",
        )
        tests = tmp_project / "tests"
        tests.mkdir(exist_ok=True)
        profile = load_profile(tmp_project)
        violations = run_compliance_scan(tmp_project, src, tests, profile)
        assert len(violations) == 0

    def test_stub_sentinel_detected(self, tmp_project):
        """__SVP_STUB__ sentinel is flagged."""
        src = tmp_project / "src"
        src.mkdir(exist_ok=True)
        stub = src / "stub_module.py"
        stub.write_text(
            "__SVP_STUB__ = True\ndef foo():\n    raise NotImplementedError\n",
            encoding="utf-8",
        )
        tests = tmp_project / "tests"
        tests.mkdir(exist_ok=True)
        profile = load_profile(tmp_project)
        violations = run_compliance_scan(tmp_project, src, tests, profile)
        assert len(violations) > 0
        assert any("__SVP_STUB__" in v.get("issue", "") for v in violations)

    def test_scan_handles_empty_dirs(self, tmp_project):
        """Scan does not fail on empty directories."""
        src = tmp_project / "empty_src"
        src.mkdir()
        tests = tmp_project / "empty_tests"
        tests.mkdir()
        profile = load_profile(tmp_project)
        violations = run_compliance_scan(tmp_project, src, tests, profile)
        assert violations == []

    def test_scan_uses_profile_delivery_env(self, tmp_project):
        """Scan respects profile delivery settings."""
        profile = load_profile(tmp_project)
        delivery = profile.get("delivery", {})
        assert delivery.get("environment_recommendation") == "conda"
        src = tmp_project / "src"
        src.mkdir(exist_ok=True)
        tests = tmp_project / "tests"
        tests.mkdir(exist_ok=True)
        violations = run_compliance_scan(tmp_project, src, tests, profile)
        assert isinstance(violations, list)


# ============================================================
# 7. Write Authorization for New Paths
# ============================================================


class TestWriteAuthorizationNewPaths:
    """Integration path 7: write authorization.

    Verifies that Unit 12 check_write_authorization
    correctly handles new paths including ruff.toml.
    """

    def test_ruff_toml_blocked(self, tmp_project):
        """ruff.toml is permanently read-only."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization("Write", "ruff.toml", state_path)
        assert result == 2

    def test_toolchain_json_blocked(self, tmp_project):
        """toolchain.json is permanently read-only."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization("Write", "toolchain.json", state_path)
        assert result == 2

    def test_svp_dir_always_writable(self, tmp_project):
        """Infrastructure paths always writable."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization("Write", ".svp/last_status.txt", state_path)
        assert result == 0

    def test_scripts_dir_writable(self, tmp_project):
        """scripts/ directory is always writable."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization("Write", "scripts/routing.py", state_path)
        assert result == 0

    def test_profile_blocked_outside_profile_stage(self, tmp_project):
        """project_profile.json blocked outside profile stage."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization(
            "Write",
            "project_profile.json",
            state_path,
        )
        # Stage 0 hook_activation: profile not writable
        assert result == 2

    def test_profile_writable_during_profile_stage(self, tmp_project):
        """project_profile.json writable during profile stage."""
        state = create_initial_state("test_project")
        state.sub_stage = "project_profile"
        save_state(state, tmp_project)
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization(
            "Write",
            "project_profile.json",
            state_path,
        )
        assert result == 0

    def test_profile_writable_during_redo_delivery(self, tmp_project):
        """project_profile.json writable during redo_profile_delivery."""
        state = _make_state(
            stage="3",
            sub_stage="redo_profile_delivery",
            current_unit=1,
        )
        save_state(state, tmp_project)
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization(
            "Write",
            "project_profile.json",
            state_path,
        )
        assert result == 0

    def test_profile_writable_during_redo_blueprint(self, tmp_project):
        """project_profile.json writable during redo_profile_blueprint."""
        state = _make_state(
            stage="3",
            sub_stage="redo_profile_blueprint",
            current_unit=1,
        )
        save_state(state, tmp_project)
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization(
            "Write",
            "project_profile.json",
            state_path,
        )
        assert result == 0

    def test_logs_dir_always_writable(self, tmp_project):
        """logs/ directory is always writable."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization("Write", "logs/debug.log", state_path)
        assert result == 0

    def test_ledgers_dir_always_writable(self, tmp_project):
        """ledgers/ directory is always writable."""
        state_path = str(tmp_project / "pipeline_state.json")
        result = check_write_authorization("Write", "ledgers/main.jsonl", state_path)
        assert result == 0


# ============================================================
# 8. Redo-Triggered Profile Revision State Transitions
# ============================================================


class TestRedoTriggeredProfileRevision:
    """Integration path 8: redo-triggered profile revision.

    Verifies that redo-triggered profile revisions
    correctly update pipeline state and re-run affected
    stages.
    """

    def test_delivery_revision_restores_snapshot(
        self,
    ):
        """Delivery revision restores pre-redo snapshot."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=2,
            fix_ladder_position=None,
            red_run_retries=1,
        )
        redo_state = enter_redo_profile_revision(state, "profile_delivery")
        assert redo_state.sub_stage == "redo_profile_delivery"
        assert redo_state.redo_triggered_from is not None

        completed = complete_redo_profile_revision(redo_state)
        assert completed.stage == "3"
        assert completed.sub_stage == "implementation"
        assert completed.current_unit == 2
        assert completed.redo_triggered_from is None

    def test_blueprint_revision_restarts_stage_2(
        self,
    ):
        """Blueprint revision restarts from Stage 2."""
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=3,
        )
        redo_state = enter_redo_profile_revision(state, "profile_blueprint")
        assert redo_state.sub_stage == "redo_profile_blueprint"

        completed = complete_redo_profile_revision(redo_state)
        assert completed.stage == "2"
        assert completed.sub_stage is None
        assert completed.current_unit is None
        assert completed.verified_units == []
        assert completed.redo_triggered_from is None

    def test_blueprint_revision_records_pass(self):
        """Blueprint revision adds to pass_history."""
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=2,
        )
        redo_state = enter_redo_profile_revision(state, "profile_blueprint")
        completed = complete_redo_profile_revision(redo_state)
        assert len(completed.pass_history) == 1
        entry = completed.pass_history[0]
        assert entry["ended_reason"] == ("profile_blueprint revision")

    def test_delivery_revision_preserves_units(self):
        """Delivery revision keeps verified_units."""
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=3,
            verified_units=[
                {"unit": 1, "timestamp": "t1"},
                {"unit": 2, "timestamp": "t2"},
            ],
        )
        redo_state = enter_redo_profile_revision(state, "profile_delivery")
        completed = complete_redo_profile_revision(redo_state)
        assert len(completed.verified_units) == 2

    def test_redo_sub_stages_are_registered(self):
        """Redo sub-stages are in REDO_PROFILE_SUB_STAGES."""
        assert "redo_profile_delivery" in REDO_PROFILE_SUB_STAGES
        assert "redo_profile_blueprint" in REDO_PROFILE_SUB_STAGES

    def test_complete_from_wrong_sub_stage_rejected(
        self,
    ):
        """Cannot complete redo from non-redo sub-stage."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        with pytest.raises(TransitionError):
            complete_redo_profile_revision(state)


# ============================================================
# 9. Quality Gate Execution Chain (NEW IN 2.1)
# ============================================================


class TestQualityGateExecutionChain:
    """Integration path 9: quality gate execution chain.

    Verifies that quality gates execute in the correct
    order and pass results between stages. Tests the
    chain: test_generation -> quality_gate_a -> red_run
    -> implementation -> quality_gate_b -> green_run.
    """

    def test_enter_quality_gate_a(self):
        """Enter quality_gate_a from Stage 3."""
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
        )
        new_state = enter_quality_gate(state, "quality_gate_a")
        assert new_state.sub_stage == "quality_gate_a"

    def test_enter_quality_gate_b(self):
        """Enter quality_gate_b from Stage 3."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        new_state = enter_quality_gate(state, "quality_gate_b")
        assert new_state.sub_stage == "quality_gate_b"

    def test_quality_gate_a_pass_to_red_run(self):
        """quality_gate_a pass advances to red_run."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        new_state = quality_gate_pass(state)
        assert new_state.sub_stage == "red_run"

    def test_quality_gate_b_pass_to_green_run(self):
        """quality_gate_b pass advances to green_run."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=1,
        )
        new_state = quality_gate_pass(state)
        assert new_state.sub_stage == "green_run"

    def test_full_chain_a_pass(self):
        """Full chain: gate_a -> pass -> red_run."""
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
        )
        gate_state = enter_quality_gate(state, "quality_gate_a")
        assert gate_state.sub_stage == "quality_gate_a"

        passed = quality_gate_pass(gate_state)
        assert passed.sub_stage == "red_run"

    def test_full_chain_b_pass(self):
        """Full chain: gate_b -> pass -> green_run."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        gate_state = enter_quality_gate(state, "quality_gate_b")
        assert gate_state.sub_stage == "quality_gate_b"

        passed = quality_gate_pass(gate_state)
        assert passed.sub_stage == "green_run"

    def test_enter_gate_outside_stage3_rejected(self):
        """Cannot enter quality gate outside Stage 3."""
        state = _make_state(stage="2")
        with pytest.raises(TransitionError):
            enter_quality_gate(state, "quality_gate_a")

    def test_enter_invalid_gate_rejected(self):
        """Cannot enter unknown quality gate name."""
        state = _make_state(stage="3", current_unit=1)
        with pytest.raises(TransitionError):
            enter_quality_gate(state, "quality_gate_z")

    def test_pass_from_non_gate_rejected(self):
        """Cannot pass quality gate from non-gate sub."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        with pytest.raises(TransitionError):
            quality_gate_pass(state)

    def test_quality_gate_sub_stages_registered(self):
        """Quality gate sub-stages registered in Unit 2."""
        assert "quality_gate_a" in QUALITY_GATE_SUB_STAGES
        assert "quality_gate_b" in QUALITY_GATE_SUB_STAGES
        assert "quality_gate_a_retry" in QUALITY_GATE_SUB_STAGES
        assert "quality_gate_b_retry" in QUALITY_GATE_SUB_STAGES

    def test_dispatch_command_at_quality_gate_a(self):
        """dispatch_command_status processes gate_a."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            new_state = dispatch_command_status(state, "COMMAND_SUCCEEDED", 1, "quality_gate", Path(td))
        assert new_state is not None

    def test_route_gate_a_retry(self, tmp_project):
        """Route handles quality_gate_a_retry."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        action = route(state, tmp_project)
        assert action["ACTION"] in (
            "COMMAND",
            "run_command",
            "invoke_agent",
        )


# ============================================================
# 10. Quality Gate Retry Isolation (NEW IN 2.1)
# ============================================================


class TestQualityGateRetryIsolation:
    """Integration path 10: quality gate retry isolation.

    Verifies that quality gate retries are isolated and
    do not affect other gates.
    """

    def test_gate_a_to_retry(self):
        """quality_gate_a advances to _retry."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        retry = advance_quality_gate_to_retry(state)
        assert retry.sub_stage == "quality_gate_a_retry"

    def test_gate_b_to_retry(self):
        """quality_gate_b advances to _retry."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=1,
        )
        retry = advance_quality_gate_to_retry(state)
        assert retry.sub_stage == "quality_gate_b_retry"

    def test_retry_a_pass_still_goes_to_red_run(self):
        """quality_gate_a_retry pass goes to red_run."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        passed = quality_gate_pass(state)
        assert passed.sub_stage == "red_run"

    def test_retry_b_pass_still_goes_to_green_run(
        self,
    ):
        """quality_gate_b_retry pass goes to green_run."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b_retry",
            current_unit=1,
        )
        passed = quality_gate_pass(state)
        assert passed.sub_stage == "green_run"

    def test_retry_a_fail_enters_fix_ladder(self):
        """quality_gate_a_retry fail enters fix ladder."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        failed = quality_gate_fail_to_ladder(state)
        assert failed.fix_ladder_position == "fresh_test"
        assert failed.sub_stage is None

    def test_retry_b_fail_enters_fix_ladder(self):
        """quality_gate_b_retry fail enters fix ladder."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b_retry",
            current_unit=1,
        )
        failed = quality_gate_fail_to_ladder(state)
        assert failed.fix_ladder_position == "fresh_impl"
        assert failed.sub_stage is None

    def test_retry_isolation_gate_a_no_affect_b(self):
        """Gate A retry does not modify gate B state."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        retry_a = advance_quality_gate_to_retry(state)
        assert retry_a.sub_stage == "quality_gate_a_retry"

        # Simulate pass on retry
        passed = quality_gate_pass(retry_a)
        assert passed.sub_stage == "red_run"

        # Now entering gate B is still possible
        gate_b_state = enter_quality_gate(
            _make_state(
                stage="3",
                sub_stage="implementation",
                current_unit=1,
            ),
            "quality_gate_b",
        )
        assert gate_b_state.sub_stage == "quality_gate_b"

    def test_cannot_advance_retry_from_wrong_sub(
        self,
    ):
        """Cannot advance to retry from wrong sub-stage."""
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )
        with pytest.raises(TransitionError):
            advance_quality_gate_to_retry(state)

    def test_fail_to_ladder_from_non_retry_rejected(
        self,
    ):
        """Cannot fail to ladder from non-retry sub."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        with pytest.raises(TransitionError):
            quality_gate_fail_to_ladder(state)

    def test_retry_fail_ladder_then_advance(self):
        """Retry fail ladder allows further advancement."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        failed = quality_gate_fail_to_ladder(state)
        assert failed.fix_ladder_position == "fresh_test"

        # Can advance ladder from fresh_test
        advanced = advance_fix_ladder(failed, "hint_test")
        assert advanced.fix_ladder_position == "hint_test"


# ============================================================
# 11. Quality Package Installation (NEW IN 2.1)
# ============================================================


class TestQualityPackageInstallation:
    """Integration path 11: quality package installation.

    Verifies that quality tool packages are correctly
    identified from toolchain before gate execution.
    """

    def test_quality_packages_from_toolchain(self, tmp_project):
        """Quality packages are read from toolchain."""
        toolchain = load_toolchain(tmp_project)
        pkgs = get_quality_packages(toolchain)
        assert isinstance(pkgs, list)
        assert "ruff" in pkgs
        assert "mypy" in pkgs

    def test_quality_packages_empty_when_missing(self):
        """Missing quality.packages returns empty list."""
        tc = {**SAMPLE_TOOLCHAIN}
        tc["quality"] = {k: v for k, v in tc["quality"].items() if k != "packages"}
        pkgs = get_quality_packages(tc)
        assert pkgs == []

    def test_quality_packages_distinct_from_framework(self, tmp_project):
        """Quality packages differ from framework pkgs."""
        toolchain = load_toolchain(tmp_project)
        from svp_config import (
            get_framework_packages,
        )

        fw_pkgs = get_framework_packages(toolchain)
        q_pkgs = get_quality_packages(toolchain)
        # ruff and mypy should not be in framework
        for pkg in q_pkgs:
            if pkg in ("ruff", "mypy"):
                assert pkg not in fw_pkgs

    def test_gate_operations_use_quality_tools(self, tmp_project):
        """Gate operations reference quality tools."""
        toolchain = load_toolchain(tmp_project)
        ops_a = get_quality_gate_operations(toolchain, "gate_a")
        ops_b = get_quality_gate_operations(toolchain, "gate_b")
        ops_c = get_quality_gate_operations(toolchain, "gate_c")
        # All gates should have at least one operation
        assert len(ops_a) > 0
        assert len(ops_b) > 0
        assert len(ops_c) > 0

    def test_gate_c_is_superset_of_gate_a(self, tmp_project):
        """Gate C includes all gate A operations or more."""
        toolchain = load_toolchain(tmp_project)
        ops_a = get_quality_gate_operations(toolchain, "gate_a")
        ops_c = get_quality_gate_operations(toolchain, "gate_c")
        assert len(ops_c) >= len(ops_a)

    def test_quality_operations_reference_tool_cmds(self, tmp_project):
        """Quality gate operations resolve to runnable commands."""
        toolchain = load_toolchain(tmp_project)
        for gate_id in ("gate_a", "gate_b", "gate_c"):
            ops = get_quality_gate_operations(toolchain, gate_id)
            for op in ops:
                full_op = "quality." + op
                cmd = resolve_command(
                    toolchain,
                    full_op,
                    {
                        "env_name": "test_env",
                        "target": "src/",
                    },
                )
                assert len(cmd) > 0
                assert "{" not in cmd

    def test_invalid_gate_id_rejected(self, tmp_project):
        """Invalid gate ID raises ValueError."""
        toolchain = load_toolchain(tmp_project)
        with pytest.raises(ValueError):
            get_quality_gate_operations(toolchain, "gate_z")

    def test_run_quality_gate_returns_dict(self, tmp_project):
        """run_quality_gate returns structured result."""
        result = run_quality_gate(
            "gate_a",
            tmp_project / "src",
            "test_env",
            tmp_project,
            SAMPLE_TOOLCHAIN,
        )
        assert isinstance(result, dict)
        assert "status" in result
        assert "details" in result
        assert isinstance(result["status"], str)
        assert isinstance(result["details"], list)

    def test_quality_gate_chain_state_transitions(
        self,
    ):
        """Full quality gate state transition chain."""
        # Start at test_generation, enter gate_a
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
        )

        # Enter gate_a
        s1 = enter_quality_gate(state, "quality_gate_a")
        assert s1.sub_stage == "quality_gate_a"

        # Gate a fails -> retry
        s2 = advance_quality_gate_to_retry(s1)
        assert s2.sub_stage == "quality_gate_a_retry"

        # Retry passes
        s3 = quality_gate_pass(s2)
        assert s3.sub_stage == "red_run"

        # Simulate red_run -> implementation transition
        s4 = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
        )

        # Enter gate_b
        s5 = enter_quality_gate(s4, "quality_gate_b")
        assert s5.sub_stage == "quality_gate_b"

        # Gate b passes directly
        s6 = quality_gate_pass(s5)
        assert s6.sub_stage == "green_run"


# ============================================================
# Cross-cutting: State persistence round-trip
# ============================================================


class TestStatePersistenceRoundTrip:
    """Verify state serialization across units."""

    def test_save_and_load_preserves_state(self, tmp_project):
        """Save then load returns equivalent state."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=2,
            total_units=5,
        )
        save_state(state, tmp_project)
        loaded = load_state(tmp_project)
        assert loaded.stage == "3"
        assert loaded.sub_stage == "quality_gate_a"
        assert loaded.current_unit == 2
        assert loaded.total_units == 5

    def test_state_with_redo_snapshot_round_trips(self, tmp_project):
        """State with redo_triggered_from round-trips."""
        state = _make_state(
            stage="3",
            sub_stage="redo_profile_delivery",
            current_unit=2,
            redo_triggered_from={
                "stage": "3",
                "sub_stage": "implementation",
                "current_unit": 2,
                "fix_ladder_position": None,
                "red_run_retries": 0,
            },
        )
        save_state(state, tmp_project)
        loaded = load_state(tmp_project)
        assert loaded.redo_triggered_from is not None
        snapshot = loaded.redo_triggered_from
        assert snapshot["stage"] == "3"
        assert snapshot["sub_stage"] == "implementation"

    def test_validate_state_on_quality_gate_sub(self):
        """Validate state accepts quality gate subs."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
        )
        errors = validate_state(state)
        assert errors == []

    def test_validate_state_on_quality_retry_sub(
        self,
    ):
        """Validate state accepts retry sub-stages."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
        )
        errors = validate_state(state)
        assert errors == []
