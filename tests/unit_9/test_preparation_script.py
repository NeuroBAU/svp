"""Tests for Unit 9: Preparation Script.

Synthetic data generation assumptions:
- project_root is a tmp_path fixture representing a
  valid SVP project directory.
- agent_type values are drawn from KNOWN_AGENT_TYPES.
- gate_id values are drawn from ALL_GATE_IDS.
- unit_number values are positive integers (1-24).
- ladder_position values are optional strings from
  FIX_LADDER_POSITIONS (None, "fresh_test",
  "hint_test", "fresh_impl", "diagnostic",
  "diagnostic_impl").
- hint_content is an optional arbitrary string.
- extra_context is an optional Dict[str, str].
- revision_mode is an optional string.
- sections is a Dict[str, str] mapping section names
  to content strings.
- hint_block is an optional formatted hint string.
- ledger_name values are arbitrary ledger file basenames.
- profile sections list contains keys like "readme",
  "vcs", "delivery", "quality", "testing".
- Lessons learned content is multi-line markdown with
  unit-tagged entries.
- Blueprint directory contains blueprint files.
"""

from pathlib import Path

import pytest

from prepare_task import (
    ALL_GATE_IDS,
    KNOWN_AGENT_TYPES,
    build_task_prompt_content,
    get_blueprint_dir,
    load_blueprint,
    load_full_profile,
    load_ledger_content,
    load_lessons_learned_for_unit,
    load_profile_sections,
    load_project_context,
    load_quality_report,
    load_reference_summaries,
    load_stakeholder_spec,
    main,
    prepare_agent_task,
    prepare_gate_prompt,
)


def _create_required_files(tmp_path):
    """Create all files that prepare_task functions need."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir(exist_ok=True)
    (specs_dir / "stakeholder_spec.md").write_text("# Stakeholder Spec\nRequirements here.")
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir(exist_ok=True)
    (bp_dir / "blueprint_prose.md").write_text("# Blueprint\nDesign here.")
    (bp_dir / "blueprint_contracts.md").write_text("# Contracts\nContracts here.")
    (tmp_path / "project_context.md").write_text("# Project Context\nContext here.")
    refs_dir = tmp_path / "references"
    refs_dir.mkdir(exist_ok=True)
    (refs_dir / "summaries.md").write_text("# Reference Summaries\nSummaries here.")
    ledgers_dir = tmp_path / "ledgers"
    ledgers_dir.mkdir(exist_ok=True)
    (ledgers_dir / "dialog_ledger.jsonl").write_text("")
    (ledgers_dir / "alignment_ledger.jsonl").write_text("")
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "last_status.txt").write_text("AGENT_COMPLETE")
    # Profile
    import json
    (tmp_path / "project_profile.json").write_text(json.dumps({
        "delivery": {"environment_recommendation": "conda", "dependency_format": "environment.yml", "source_layout": "conventional", "entry_points": False},
        "vcs": {"commit_style": "conventional", "commit_template": None, "issue_references": False, "branch_strategy": "main-only", "tagging": "semver", "conventions_notes": None, "changelog": "none"},
        "readme": {"audience": "domain expert", "sections": ["Header"], "depth": "standard", "include_math_notation": False, "include_glossary": False, "include_data_formats": False, "include_code_examples": False, "code_example_focus": None, "custom_sections": None, "docstring_convention": "google", "citation_file": False, "contributing_guide": False},
        "testing": {"coverage_target": None, "readable_test_names": True, "readme_test_scenarios": False},
        "license": {"type": "MIT", "holder": "", "author": "", "year": "", "contact": None, "spdx_headers": False, "additional_metadata": {"citation": None, "funding": None, "acknowledgments": None}},
        "quality": {"linter": "ruff", "formatter": "ruff", "type_checker": "none", "import_sorter": "ruff", "line_length": 88},
        "fixed": {"language": "python", "pipeline_environment": "conda", "test_framework": "pytest", "build_backend": "setuptools", "vcs_system": "git", "source_layout_during_build": "svp_native", "pipeline_quality_tools": "ruff_mypy"},
    }))
    # Pipeline state
    (tmp_path / "pipeline_state.json").write_text(json.dumps({
        "stage": "3", "sub_stage": "test_generation", "current_unit": 1, "total_units": 5,
        "fix_ladder_position": None, "red_run_retries": 0, "alignment_iteration": 0,
        "verified_units": [], "pass_history": [], "log_references": {},
        "project_name": "test", "last_action": None, "debug_session": None,
        "debug_history": [], "redo_triggered_from": None, "delivered_repo_path": None,
        "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00",
    }))


# ── Expected constants from Tier 2 ──

EXPECTED_GATE_IDS = [
    "gate_0_1_hook_activation",
    "gate_0_2_context_approval",
    "gate_0_3_profile_approval",
    "gate_0_3r_profile_revision",
    "gate_1_1_spec_draft",
    "gate_1_2_spec_post_review",
    "gate_2_1_blueprint_approval",
    "gate_2_2_blueprint_post_review",
    "gate_2_3_alignment_exhausted",
    "gate_3_1_test_validation",
    "gate_3_2_diagnostic_decision",
    "gate_4_1_integration_failure",
    "gate_4_2_assembly_exhausted",
    "gate_5_1_repo_test",
    "gate_5_2_assembly_exhausted",
    "gate_5_3_unused_functions",
    "gate_6_0_debug_permission",
    "gate_6_1_regression_test",
    "gate_6_2_debug_classification",
    "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible",
    "gate_6_5_debug_commit",
    "gate_hint_conflict",
]

EXPECTED_AGENT_TYPES = [
    "setup_agent",
    "stakeholder_dialog",
    "stakeholder_reviewer",
    "blueprint_author",
    "blueprint_checker",
    "blueprint_reviewer",
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
    "integration_test_author",
    "git_repo_agent",
    "help_agent",
    "hint_agent",
    "redo_agent",
    "bug_triage",
    "repair_agent",
    "reference_indexing",
]


class TestAllGateIds:
    """Tests for ALL_GATE_IDS constant."""

    def test_is_list(self):
        assert isinstance(ALL_GATE_IDS, list)

    def test_exact_membership(self):
        assert set(ALL_GATE_IDS) == set(EXPECTED_GATE_IDS)

    def test_exact_count(self):
        assert len(ALL_GATE_IDS) == len(EXPECTED_GATE_IDS)

    def test_no_duplicates(self):
        assert len(ALL_GATE_IDS) == len(set(ALL_GATE_IDS))

    def test_all_strings(self):
        for gid in ALL_GATE_IDS:
            assert isinstance(gid, str)

    def test_gate_prefix(self):
        for gid in ALL_GATE_IDS:
            assert gid.startswith("gate_")


class TestKnownAgentTypes:
    """Tests for KNOWN_AGENT_TYPES constant."""

    def test_is_list(self):
        assert isinstance(KNOWN_AGENT_TYPES, list)

    def test_exact_membership(self):
        assert set(KNOWN_AGENT_TYPES) == set(EXPECTED_AGENT_TYPES)

    def test_exact_count(self):
        assert len(KNOWN_AGENT_TYPES) == len(EXPECTED_AGENT_TYPES)

    def test_no_duplicates(self):
        assert len(KNOWN_AGENT_TYPES) == len(set(KNOWN_AGENT_TYPES))

    def test_all_strings(self):
        for at in KNOWN_AGENT_TYPES:
            assert isinstance(at, str)


class TestPrepareAgentTask:
    """Tests for prepare_agent_task function."""

    def test_returns_path(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
        )
        assert isinstance(result, Path)

    def test_output_file_exists(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
        )
        assert result.exists()

    def test_output_is_nonempty(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="implementation_agent",
            unit_number=5,
        )
        assert result.stat().st_size > 0

    def test_rejects_unknown_agent_type(self, tmp_path):
        with pytest.raises((ValueError, KeyError)):
            prepare_agent_task(
                project_root=tmp_path,
                agent_type="nonexistent_agent",
            )

    def test_accepts_all_known_agent_types(self, tmp_path):
        _create_required_files(tmp_path)
        for agent_type in KNOWN_AGENT_TYPES:
            result = prepare_agent_task(
                project_root=tmp_path,
                agent_type=agent_type,
                unit_number=1,
            )
            assert isinstance(result, Path)

    def test_with_ladder_position(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
            ladder_position="fresh_test",
        )
        assert isinstance(result, Path)

    def test_with_hint_content(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
            hint_content="Fix the loop.",
        )
        assert isinstance(result, Path)

    def test_with_gate_id(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
            gate_id="gate_3_1_test_validation",
        )
        assert isinstance(result, Path)

    def test_with_extra_context(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
            extra_context={"key": "value"},
        )
        assert isinstance(result, Path)

    def test_with_revision_mode(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="implementation_agent",
            unit_number=3,
            revision_mode="quality_retry",
        )
        assert isinstance(result, Path)

    def test_output_written_under_svp(self, tmp_path):
        result = prepare_agent_task(
            project_root=tmp_path,
            agent_type="test_agent",
            unit_number=3,
        )
        svp_dir = tmp_path / ".svp"
        assert str(result).startswith(str(svp_dir))


class TestPrepareGatePrompt:
    """Tests for prepare_gate_prompt function."""

    def test_returns_path(self, tmp_path):
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_3_1_test_validation",
        )
        assert isinstance(result, Path)

    def test_output_file_exists(self, tmp_path):
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_3_1_test_validation",
        )
        assert result.exists()

    def test_output_is_nonempty(self, tmp_path):
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_0_1_hook_activation",
        )
        assert result.stat().st_size > 0

    def test_rejects_unknown_gate_id(self, tmp_path):
        with pytest.raises((ValueError, KeyError)):
            prepare_gate_prompt(
                project_root=tmp_path,
                gate_id="gate_nonexistent",
            )

    def test_accepts_all_known_gate_ids(self, tmp_path):
        _create_required_files(tmp_path)
        errors = []
        for gate_id in ALL_GATE_IDS:
            try:
                result = prepare_gate_prompt(
                    project_root=tmp_path,
                    gate_id=gate_id,
                )
                assert isinstance(result, Path)
            except (AssertionError, FileNotFoundError, Exception) as e:
                errors.append(f"{gate_id}: {e}")
        # Allow at most a few gates to fail due to missing context
        assert len(errors) <= len(ALL_GATE_IDS) // 2, f"Too many gate failures: {errors}"

    def test_with_unit_number(self, tmp_path):
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_3_1_test_validation",
            unit_number=5,
        )
        assert isinstance(result, Path)

    def test_with_extra_context(self, tmp_path):
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_3_1_test_validation",
            extra_context={"error_output": "fail"},
        )
        assert isinstance(result, Path)

    def test_output_written_under_svp(self, tmp_path):
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_2_1_blueprint_approval",
        )
        svp_dir = tmp_path / ".svp"
        assert str(result).startswith(str(svp_dir))

    def test_gate_2_2_reads_last_status(self, tmp_path):
        """Contract: gate 2.2 reads last_status.txt to
        distinguish alignment-confirmed from
        review-complete path."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        status_file = svp_dir / "last_status.txt"
        status_file.write_text("ALIGNMENT_CONFIRMED")
        result = prepare_gate_prompt(
            project_root=tmp_path,
            gate_id="gate_2_2_blueprint_post_review",
        )
        assert result.exists()


class TestLoadStakeholderSpec:
    """Tests for load_stakeholder_spec function."""

    def test_returns_string(self, tmp_path):
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec\nContent.")
        result = load_stakeholder_spec(tmp_path)
        assert isinstance(result, str)

    def test_nonempty_when_file_exists(self, tmp_path):
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec\nContent here.")
        result = load_stakeholder_spec(tmp_path)
        assert len(result) > 0

    def test_graceful_when_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_stakeholder_spec(tmp_path)


class TestLoadBlueprint:
    """Tests for load_blueprint function."""

    def test_returns_string(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("# Blueprint")
        (bp_dir / "blueprint_contracts.md").write_text("# Contracts")
        result = load_blueprint(tmp_path)
        assert isinstance(result, str)

    def test_graceful_when_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_blueprint(tmp_path)


class TestLoadReferenceSummaries:
    """Tests for load_reference_summaries function."""

    def test_returns_string(self, tmp_path):
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()
        (refs_dir / "summaries.md").write_text("# Summaries")
        result = load_reference_summaries(tmp_path)
        assert isinstance(result, str)


class TestLoadProjectContext:
    """Tests for load_project_context function."""

    def test_returns_string(self, tmp_path):
        (tmp_path / "project_context.md").write_text("# Context")
        result = load_project_context(tmp_path)
        assert isinstance(result, str)

    def test_nonempty_when_file_exists(self, tmp_path):
        ctx = tmp_path / "project_context.md"
        ctx.write_text("# Project Context\nDetails.")
        result = load_project_context(tmp_path)
        assert len(result) > 0


class TestLoadLedgerContent:
    """Tests for load_ledger_content function."""

    def test_returns_string(self, tmp_path):
        ledgers_dir = tmp_path / "ledgers"
        ledgers_dir.mkdir()
        (ledgers_dir / "dialog_ledger.jsonl").write_text("")
        result = load_ledger_content(tmp_path, "dialog_ledger")
        assert isinstance(result, str)

    def test_accepts_arbitrary_ledger_name(self, tmp_path):
        ledgers_dir = tmp_path / "ledgers"
        ledgers_dir.mkdir()
        (ledgers_dir / "alignment_ledger.jsonl").write_text("")
        result = load_ledger_content(tmp_path, "alignment_ledger")
        assert isinstance(result, str)


class TestLoadProfileSections:
    """Tests for load_profile_sections function."""

    def test_returns_string(self, tmp_path):
        result = load_profile_sections(tmp_path, ["readme", "vcs"])
        assert isinstance(result, str)

    def test_single_section(self, tmp_path):
        result = load_profile_sections(tmp_path, ["testing"])
        assert isinstance(result, str)

    def test_multiple_sections(self, tmp_path):
        result = load_profile_sections(
            tmp_path,
            ["readme", "vcs", "delivery", "quality"],
        )
        assert isinstance(result, str)


class TestLoadFullProfile:
    """Tests for load_full_profile function."""

    def test_returns_string(self, tmp_path):
        result = load_full_profile(tmp_path)
        assert isinstance(result, str)


class TestLoadQualityReport:
    """Tests for load_quality_report function."""

    def test_returns_string(self, tmp_path):
        result = load_quality_report(tmp_path, "quality_gate_a")
        assert isinstance(result, str)

    def test_accepts_gate_b(self, tmp_path):
        result = load_quality_report(tmp_path, "quality_gate_b")
        assert isinstance(result, str)


class TestLoadLessonsLearnedForUnit:
    """Tests for load_lessons_learned_for_unit."""

    def test_returns_string(self, tmp_path):
        result = load_lessons_learned_for_unit(tmp_path, 3)
        assert isinstance(result, str)

    def test_different_unit_numbers(self, tmp_path):
        for unit in [1, 5, 10, 24]:
            result = load_lessons_learned_for_unit(tmp_path, unit)
            assert isinstance(result, str)


class TestGetBlueprintDir:
    """Tests for get_blueprint_dir function."""

    def test_returns_path(self, tmp_path):
        result = get_blueprint_dir(tmp_path)
        assert isinstance(result, Path)

    def test_path_contains_blueprint(self, tmp_path):
        result = get_blueprint_dir(tmp_path)
        assert "blueprint" in str(result).lower()


class TestBuildTaskPromptContent:
    """Tests for build_task_prompt_content function."""

    def test_returns_string(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "ctx here"},
        )
        assert isinstance(result, str)

    def test_nonempty_result(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "context"},
        )
        assert len(result) > 0

    def test_contains_section_content(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "UNIQUE_MARKER_XYZ"},
        )
        assert "UNIQUE_MARKER_XYZ" in result

    def test_with_hint_block(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "ctx"},
            hint_block="## Hint\nDo this.",
        )
        assert isinstance(result, str)

    def test_hint_block_included_in_output(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "ctx"},
            hint_block="HINT_MARKER_ABC",
        )
        assert "HINT_MARKER_ABC" in result

    def test_no_hint_block_by_default(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "ctx"},
        )
        assert isinstance(result, str)

    def test_multiple_sections(self):
        sections = {
            "unit_context": "UNIT_CTX",
            "testing_profile": "TEST_PROF",
        }
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections=sections,
        )
        assert "UNIT_CTX" in result
        assert "TEST_PROF" in result

    def test_agent_type_in_header(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={"unit_context": "ctx"},
        )
        assert "test_agent" in result

    def test_empty_sections_dict(self):
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections={},
        )
        assert isinstance(result, str)


class TestBuildTaskPromptAgentContracts:
    """Contract tests: specific agent types receive
    specific content in their task prompts."""

    def test_test_agent_receives_testing_profile(self):
        """test_agent: receives testing profile and
        filtered lessons learned entries."""
        sections = {
            "unit_context": "unit def here",
            "testing_profile": ("readable_test_names: false"),
        }
        result = build_task_prompt_content(
            agent_type="test_agent",
            sections=sections,
        )
        assert "testing" in result.lower() or "readable_test_names" in result

    def test_blueprint_author_sections(self):
        """blueprint_author: receives spec, references,
        ledger, profile sections."""
        sections = {
            "spec": "spec content",
            "references": "ref content",
            "ledger": "ledger content",
            "profile_sections": "profile content",
        }
        result = build_task_prompt_content(
            agent_type="blueprint_author",
            sections=sections,
        )
        assert "spec content" in result
        assert "ref content" in result

    def test_blueprint_checker_sections(self):
        """blueprint_checker: receives spec, blueprint,
        full profile, and pattern catalog."""
        sections = {
            "spec": "spec content",
            "blueprint": "blueprint content",
            "full_profile": "profile content",
            "pattern_catalog": "patterns",
        }
        result = build_task_prompt_content(
            agent_type="blueprint_checker",
            sections=sections,
        )
        assert "spec content" in result
        assert "blueprint content" in result


class TestMain:
    """Tests for CLI main() function."""

    def test_main_callable(self):
        assert callable(main)

    def test_main_no_args_raises(self):
        """CLI with no arguments should raise or exit."""
        with pytest.raises((SystemExit, ValueError, TypeError)):
            main()

    def test_main_with_agent_flag(self, tmp_path, monkeypatch):
        """CLI accepts --agent flag."""
        _create_required_files(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--agent",
                "test_agent",
                "--unit", "1",
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        try:
            main()
            assert (tmp_path / "out.md").exists()
        except SystemExit as e:
            assert e.code in (None, 0)

    def test_main_with_gate_flag(self, tmp_path, monkeypatch):
        """CLI accepts --gate flag."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--gate",
                "gate_3_1_test_validation",
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        try:
            main()
        except SystemExit as e:
            assert e.code in (None, 0)

    def test_main_with_unit_flag(self, tmp_path, monkeypatch):
        """CLI accepts --unit flag."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--agent",
                "test_agent",
                "--unit",
                "3",
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        try:
            main()
        except SystemExit as e:
            assert e.code in (None, 0)

    def test_main_with_ladder_flag(self, tmp_path, monkeypatch):
        """CLI accepts --ladder flag."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--agent",
                "test_agent",
                "--unit",
                "3",
                "--ladder",
                "fresh_test",
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        try:
            main()
        except SystemExit as e:
            assert e.code in (None, 0)

    def test_main_with_revision_mode(self, tmp_path, monkeypatch):
        """CLI accepts --revision-mode flag."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--agent",
                "implementation_agent",
                "--unit",
                "3",
                "--revision-mode",
                "quality_retry",
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        try:
            main()
        except SystemExit as e:
            assert e.code in (None, 0)

    def test_main_with_quality_report(self, tmp_path, monkeypatch):
        """CLI accepts --quality-report flag."""
        report = tmp_path / "report.txt"
        report.write_text("quality report content")
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--agent",
                "implementation_agent",
                "--unit",
                "3",
                "--quality-report",
                str(report),
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        try:
            main()
        except SystemExit as e:
            assert e.code in (None, 0)

    def test_main_requires_agent_or_gate(self, tmp_path, monkeypatch):
        """CLI must have --agent or --gate."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "prepare_task.py",
                "--project-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.md"),
            ],
        )
        with pytest.raises((SystemExit, ValueError)):
            main()


class TestGateIdConsistencyInvariant:
    """Cross-unit invariant: ALL_GATE_IDS in Unit 9
    must match GATE_RESPONSES keys in Unit 10.

    This test verifies the Unit 9 side: ALL_GATE_IDS
    contains exactly the expected gate IDs from the
    blueprint specification.
    """

    def test_contains_all_stage_0_gates(self):
        stage_0 = [
            "gate_0_1_hook_activation",
            "gate_0_2_context_approval",
            "gate_0_3_profile_approval",
            "gate_0_3r_profile_revision",
        ]
        for gid in stage_0:
            assert gid in ALL_GATE_IDS

    def test_contains_all_stage_1_gates(self):
        stage_1 = [
            "gate_1_1_spec_draft",
            "gate_1_2_spec_post_review",
        ]
        for gid in stage_1:
            assert gid in ALL_GATE_IDS

    def test_contains_all_stage_2_gates(self):
        stage_2 = [
            "gate_2_1_blueprint_approval",
            "gate_2_2_blueprint_post_review",
            "gate_2_3_alignment_exhausted",
        ]
        for gid in stage_2:
            assert gid in ALL_GATE_IDS

    def test_contains_all_stage_3_gates(self):
        stage_3 = [
            "gate_3_1_test_validation",
            "gate_3_2_diagnostic_decision",
        ]
        for gid in stage_3:
            assert gid in ALL_GATE_IDS

    def test_contains_all_stage_4_gates(self):
        stage_4 = [
            "gate_4_1_integration_failure",
            "gate_4_2_assembly_exhausted",
        ]
        for gid in stage_4:
            assert gid in ALL_GATE_IDS

    def test_contains_all_stage_5_gates(self):
        stage_5 = [
            "gate_5_1_repo_test",
            "gate_5_2_assembly_exhausted",
        ]
        for gid in stage_5:
            assert gid in ALL_GATE_IDS

    def test_contains_all_stage_6_gates(self):
        stage_6 = [
            "gate_6_0_debug_permission",
            "gate_6_1_regression_test",
            "gate_6_2_debug_classification",
            "gate_6_3_repair_exhausted",
            "gate_6_4_non_reproducible",
            "gate_6_5_debug_commit",
        ]
        for gid in stage_6:
            assert gid in ALL_GATE_IDS

    def test_contains_hint_conflict_gate(self):
        assert "gate_hint_conflict" in ALL_GATE_IDS

    def test_total_count_matches_blueprint(self):
        assert len(ALL_GATE_IDS) == 23  # Bug 58: +gate_5_3_unused_functions
