"""
Test suite for Unit 22: Project Templates

Tests cover:
- generate_claude_md function: signature, output content, error conditions
- Template file path constants
- Deliverable content constants (CLAUDE_MD_PY_CONTENT, SVP_CONFIG_DEFAULT_JSON_CONTENT,
  PIPELINE_STATE_INITIAL_JSON_CONTENT, README_SVP_TXT_CONTENT)
- Game of Life example content constants (GOL_STAKEHOLDER_SPEC_CONTENT,
  GOL_BLUEPRINT_CONTENT, GOL_PROJECT_CONTEXT_CONTENT)
- All invariants from the blueprint
- All error conditions from the blueprint
- All behavioral contracts from the blueprint

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: Project names are short alphanumeric strings like
"test_project" or "my-app", representing typical project directory names
that a user might choose when bootstrapping a new SVP project.

DATA ASSUMPTION: Project roots are temporary directories created via
tmp_path, representing valid filesystem directories.

DATA ASSUMPTION: The DEFAULT_CONFIG from Unit 1 is used as the reference
for the config template content. The specific values (iteration_limit=3,
models dict with claude-opus-4-6/claude-sonnet-4-6, etc.) come from the
Unit 1 blueprint contract.

DATA ASSUMPTION: The initial pipeline state template uses stage "0",
sub_stage "hook_activation", null counters, empty lists, and null
timestamps -- matching Unit 2's create_initial_state contract.

DATA ASSUMPTION: Empty string "" is used to test the ValueError for
empty project name. This is the most straightforward empty-string case.
==========================================================================
"""

import json
import inspect
import pytest
from pathlib import Path
from typing import Dict, Any

from svp.scripts.project_templates import (
    generate_claude_md,
    DEFAULT_CONFIG_TEMPLATE,
    INITIAL_STATE_TEMPLATE,
    README_SVP_TEMPLATE,
)

# Upstream contract reference: Unit 1 DEFAULT_CONFIG
from svp.scripts.svp_config import DEFAULT_CONFIG as UNIT_1_DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# Helper: safely import MD_CONTENT constants
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name.

    The stub declares these as type annotations without values, so
    direct import will fail on the stub (red run) and succeed on
    the implementation (green run).
    """
    import svp.scripts.project_templates as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.project_templates")
    return val


# ===========================================================================
# 1. Signature verification
# ===========================================================================


class TestSignatures:
    """Verify function and constant signatures match the blueprint."""

    def test_generate_claude_md_is_callable(self):
        assert callable(generate_claude_md)

    def test_generate_claude_md_parameters(self):
        sig = inspect.signature(generate_claude_md)
        param_names = list(sig.parameters.keys())
        assert "project_name" in param_names
        assert "project_root" in param_names

    def test_generate_claude_md_parameter_annotations(self):
        sig = inspect.signature(generate_claude_md)
        assert sig.parameters["project_name"].annotation == str
        assert sig.parameters["project_root"].annotation == Path

    def test_generate_claude_md_return_annotation(self):
        sig = inspect.signature(generate_claude_md)
        assert sig.return_annotation == str

    def test_default_config_template_is_string(self):
        assert isinstance(DEFAULT_CONFIG_TEMPLATE, str)

    def test_initial_state_template_is_string(self):
        assert isinstance(INITIAL_STATE_TEMPLATE, str)

    def test_readme_svp_template_is_string(self):
        assert isinstance(README_SVP_TEMPLATE, str)

    def test_claude_md_py_content_is_string(self):
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        assert isinstance(content, str)

    def test_svp_config_default_json_content_is_string(self):
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        assert isinstance(content, str)

    def test_pipeline_state_initial_json_content_is_string(self):
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        assert isinstance(content, str)

    def test_readme_svp_txt_content_is_string(self):
        content = _get_md_content("README_SVP_TXT_CONTENT")
        assert isinstance(content, str)

    def test_gol_stakeholder_spec_content_is_string(self):
        content = _get_md_content("GOL_STAKEHOLDER_SPEC_CONTENT")
        assert isinstance(content, str)

    def test_gol_blueprint_content_is_string(self):
        content = _get_md_content("GOL_BLUEPRINT_CONTENT")
        assert isinstance(content, str)

    def test_gol_project_context_content_is_string(self):
        content = _get_md_content("GOL_PROJECT_CONTEXT_CONTENT")
        assert isinstance(content, str)


# ===========================================================================
# 2. Template path constants
# ===========================================================================


class TestTemplatePathConstants:
    """Verify template file path constants have expected values."""

    def test_default_config_template_path(self):
        assert DEFAULT_CONFIG_TEMPLATE == "templates/svp_config_default.json"

    def test_initial_state_template_path(self):
        assert INITIAL_STATE_TEMPLATE == "templates/pipeline_state_initial.json"

    def test_readme_svp_template_path(self):
        assert README_SVP_TEMPLATE == "templates/readme_svp.txt"


# ===========================================================================
# 3. generate_claude_md function
# ===========================================================================


class TestGenerateClaudeMd:
    """Verify generate_claude_md behavioral contracts."""

    # DATA ASSUMPTION: "test_project" is a typical project name string
    PROJECT_NAME = "test_project"

    def test_returns_string(self, tmp_path):
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        assert isinstance(result, str)

    def test_contains_project_name(self, tmp_path):
        """Contract: produces content with the project name."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        assert self.PROJECT_NAME in result

    def test_contains_svp_managed_header(self, tmp_path):
        """Contract: produces SVP-managed project header."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        assert "SVP" in result

    def test_contains_routing_script_instruction(self, tmp_path):
        """Contract: instructs to run routing script on session start."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        assert "routing" in result.lower()

    def test_contains_six_step_action_cycle(self, tmp_path):
        """Contract: includes the six-step action cycle instruction."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        # The content must reference the six-step cycle
        assert "six" in result.lower() or "6" in result

    def test_contains_verbatim_relay_instruction(self, tmp_path):
        """Contract: includes verbatim task prompt relay instruction."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        assert "verbatim" in result.lower()

    def test_contains_do_not_improvise_section(self, tmp_path):
        """Contract: includes 'Do Not Improvise' behavioral constraint."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        # Check for the "Do Not Improvise" or similar phrasing
        lower_result = result.lower()
        assert "improvise" in lower_result or "do not improvise" in lower_result

    def test_contains_defer_human_input(self, tmp_path):
        """Contract: includes instruction to defer human input during autonomous sequences."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        lower_result = result.lower()
        assert "defer" in lower_result or "human input" in lower_result

    def test_contains_orchestration_skill_reference(self, tmp_path):
        """Contract: references the orchestration skill."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        lower_result = result.lower()
        assert "orchestration" in lower_result

    def test_with_different_project_name(self, tmp_path):
        """Verify project name is properly substituted."""
        # DATA ASSUMPTION: "my-awesome-project" is another valid project name
        result = generate_claude_md("my-awesome-project", tmp_path)
        assert "my-awesome-project" in result

    def test_output_is_nonempty(self, tmp_path):
        """The generated CLAUDE.md must have substantial content."""
        result = generate_claude_md(self.PROJECT_NAME, tmp_path)
        # A valid CLAUDE.md should have significant content
        assert len(result) > 100


# ===========================================================================
# 4. Error conditions
# ===========================================================================


class TestErrorConditions:
    """Verify error conditions from the blueprint."""

    def test_empty_project_name_raises_value_error(self, tmp_path):
        """Error: 'Project name must not be empty' for empty string."""
        with pytest.raises(ValueError, match="Project name must not be empty"):
            generate_claude_md("", tmp_path)


# ===========================================================================
# 5. Invariants: CLAUDE_MD_PY_CONTENT
# ===========================================================================


class TestClaudeMdPyContent:
    """Verify CLAUDE_MD_PY_CONTENT invariants and behavioral contracts."""

    def test_invariant_has_render_function(self):
        """Invariant: 'def render_claude_md' in CLAUDE_MD_PY_CONTENT."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        assert "def render_claude_md" in content, \
            "claude_md.py must have render function"

    def test_is_valid_python_module(self):
        """Contract: must be a non-empty, compilable Python module."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        # Must be non-empty -- an empty string is not a valid module
        assert len(content.strip()) > 0, \
            "CLAUDE_MD_PY_CONTENT must not be empty"
        # Should be compilable Python
        try:
            compile(content, "<claude_md.py>", "exec")
        except SyntaxError as e:
            pytest.fail(f"CLAUDE_MD_PY_CONTENT is not valid Python: {e}")

    def test_render_function_signature(self):
        """Contract: render_claude_md(project_name: str) -> str."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        # Execute the module to inspect the function
        namespace = {}
        exec(content, namespace)
        render_func = namespace.get("render_claude_md")
        assert render_func is not None, "render_claude_md function must exist"
        assert callable(render_func)

    def test_render_function_produces_svp_header(self):
        """Contract: generated content must include SVP-managed project header."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        # DATA ASSUMPTION: "example_proj" is a simple test project name
        result = render_func("example_proj")
        assert isinstance(result, str)
        assert "SVP" in result
        assert "example_proj" in result

    def test_render_function_includes_routing_script(self):
        """Contract: generated content must instruct to run routing script."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        result = render_func("test_proj")
        assert "routing" in result.lower()

    def test_render_function_includes_six_step_cycle(self):
        """Contract: generated content must include six-step action cycle."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        result = render_func("test_proj")
        lower_result = result.lower()
        assert "six" in lower_result or "6" in lower_result

    def test_render_function_includes_verbatim_relay(self):
        """Contract: generated content must include verbatim relay rule."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        result = render_func("test_proj")
        assert "verbatim" in result.lower()

    def test_render_function_includes_do_not_improvise(self):
        """Contract: generated content must include 'Do Not Improvise' section."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        result = render_func("test_proj")
        assert "improvise" in result.lower()

    def test_render_function_includes_orchestration_skill(self):
        """Contract: generated content must reference orchestration skill."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        result = render_func("test_proj")
        assert "orchestration" in result.lower()

    def test_content_is_nonempty(self):
        """The Python content must be substantial."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        assert len(content) > 50


# ===========================================================================
# 6. Invariants: SVP_CONFIG_DEFAULT_JSON_CONTENT
# ===========================================================================


class TestSvpConfigDefaultJsonContent:
    """Verify SVP_CONFIG_DEFAULT_JSON_CONTENT invariants and behavioral contracts."""

    def test_invariant_has_skip_permissions(self):
        """Invariant: 'skip_permissions' in SVP_CONFIG_DEFAULT_JSON_CONTENT."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        assert '"skip_permissions"' in content, \
            "Config must have skip_permissions"

    def test_is_valid_json(self):
        """Contract: must be valid JSON."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"SVP_CONFIG_DEFAULT_JSON_CONTENT is not valid JSON: {e}")
        assert isinstance(parsed, dict)

    def test_has_iteration_limit(self):
        """Contract: must have iteration_limit."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "iteration_limit" in parsed

    def test_has_models_dict(self):
        """Contract: must have models dict."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "models" in parsed
        assert isinstance(parsed["models"], dict)

    def test_has_context_budget_override(self):
        """Contract: must have context_budget_override."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "context_budget_override" in parsed

    def test_has_context_budget_threshold(self):
        """Contract: must have context_budget_threshold."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "context_budget_threshold" in parsed

    def test_has_compaction_character_threshold(self):
        """Contract: must have compaction_character_threshold."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "compaction_character_threshold" in parsed

    def test_has_auto_save(self):
        """Contract: must have auto_save."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "auto_save" in parsed

    def test_has_skip_permissions_in_parsed(self):
        """Contract: must have skip_permissions in the parsed JSON."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert "skip_permissions" in parsed

    def test_matches_unit_1_default_config(self):
        """Contract: default config template must match Unit 1's DEFAULT_CONFIG."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        # Check all keys from Unit 1 DEFAULT_CONFIG are present with same values
        assert parsed["iteration_limit"] == UNIT_1_DEFAULT_CONFIG["iteration_limit"]
        assert parsed["models"] == UNIT_1_DEFAULT_CONFIG["models"]
        assert parsed["context_budget_override"] == UNIT_1_DEFAULT_CONFIG["context_budget_override"]
        assert parsed["context_budget_threshold"] == UNIT_1_DEFAULT_CONFIG["context_budget_threshold"]
        assert parsed["compaction_character_threshold"] == UNIT_1_DEFAULT_CONFIG["compaction_character_threshold"]
        assert parsed["auto_save"] == UNIT_1_DEFAULT_CONFIG["auto_save"]
        assert parsed["skip_permissions"] == UNIT_1_DEFAULT_CONFIG["skip_permissions"]

    def test_content_is_nonempty(self):
        """The JSON content must be substantial."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        assert len(content) > 10


# ===========================================================================
# 7. Invariants: PIPELINE_STATE_INITIAL_JSON_CONTENT
# ===========================================================================


class TestPipelineStateInitialJsonContent:
    """Verify PIPELINE_STATE_INITIAL_JSON_CONTENT invariants and contracts."""

    def test_invariant_has_stage_field(self):
        """Invariant: 'stage' in PIPELINE_STATE_INITIAL_JSON_CONTENT."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        assert '"stage"' in content, \
            "Initial state must have stage field"

    def test_is_valid_json(self):
        """Contract: must be valid JSON."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"PIPELINE_STATE_INITIAL_JSON_CONTENT is not valid JSON: {e}"
            )
        assert isinstance(parsed, dict)

    def test_stage_is_zero(self):
        """Contract: initial stage is '0'."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["stage"] == "0"

    def test_sub_stage_is_hook_activation(self):
        """Contract: initial sub_stage is 'hook_activation'."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed["sub_stage"] == "hook_activation"

    def test_null_counters(self):
        """Contract: null counters (current_unit, total_units, fix_ladder_position)."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed.get("current_unit") is None
        assert parsed.get("total_units") is None
        assert parsed.get("fix_ladder_position") is None

    def test_empty_lists(self):
        """Contract: empty lists (verified_units, pass_history, debug_history)."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed.get("verified_units") == []
        assert parsed.get("pass_history") == []

    def test_zero_counters(self):
        """Contract: zero counters (red_run_retries, alignment_iteration)."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed.get("red_run_retries") == 0
        assert parsed.get("alignment_iteration") == 0

    def test_has_project_name_field(self):
        """Contract: has project_name field (placeholder or null)."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert "project_name" in parsed

    def test_null_timestamps(self):
        """Contract: null timestamps in the template (timestamps are set at creation time)."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        # The template must include timestamp fields, but as null
        # since actual timestamps are set when a project is created
        assert "created_at" in parsed
        assert "updated_at" in parsed
        assert parsed["created_at"] is None
        assert parsed["updated_at"] is None

    def test_last_action_is_null(self):
        """Contract: last_action is null in initial state."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert "last_action" in parsed
        assert parsed["last_action"] is None

    def test_debug_session_is_null(self):
        """Contract: debug_session is null in initial state."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert "debug_session" in parsed
        assert parsed["debug_session"] is None

    def test_content_is_nonempty(self):
        """The JSON content must be substantial."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        assert len(content) > 10


# ===========================================================================
# 8. Invariants: README_SVP_TXT_CONTENT
# ===========================================================================


class TestReadmeSvpTxtContent:
    """Verify README_SVP_TXT_CONTENT invariants and behavioral contracts."""

    def test_invariant_has_svp_managed(self):
        """Invariant: 'SVP-MANAGED' in README_SVP_TXT_CONTENT."""
        content = _get_md_content("README_SVP_TXT_CONTENT")
        assert "SVP-MANAGED" in content, \
            "README must have protection notice"

    def test_explains_write_authorization(self):
        """Contract: explains the two-layer write authorization system."""
        content = _get_md_content("README_SVP_TXT_CONTENT")
        lower_content = content.lower()
        # Should mention write authorization or write protection
        assert ("write" in lower_content and "authorization" in lower_content) or \
               ("write" in lower_content and "protect" in lower_content), \
            "README must explain write authorization system"

    def test_directs_to_svp_command(self):
        """Contract: directs users to use the 'svp' command."""
        content = _get_md_content("README_SVP_TXT_CONTENT")
        assert "svp" in content.lower(), \
            "README must direct users to use the svp command"

    def test_content_is_nonempty(self):
        """The text content must be substantial."""
        content = _get_md_content("README_SVP_TXT_CONTENT")
        assert len(content) > 20


# ===========================================================================
# 9. Game of Life example content
# ===========================================================================


class TestGolStakeholderSpecContent:
    """Verify GOL_STAKEHOLDER_SPEC_CONTENT invariants and contracts."""

    def test_invariant_mentions_conway(self):
        """Invariant: 'Conway' in GOL_STAKEHOLDER_SPEC_CONTENT."""
        content = _get_md_content("GOL_STAKEHOLDER_SPEC_CONTENT")
        assert "Conway" in content, \
            "GoL spec must describe Game of Life"

    def test_is_nonempty(self):
        """Content must be a substantial document."""
        content = _get_md_content("GOL_STAKEHOLDER_SPEC_CONTENT")
        assert len(content) > 50

    def test_mentions_game_of_life(self):
        """Should reference Game of Life."""
        content = _get_md_content("GOL_STAKEHOLDER_SPEC_CONTENT")
        assert "Game of Life" in content or \
               "game of life" in content.lower()


class TestGolBlueprintContent:
    """Verify GOL_BLUEPRINT_CONTENT invariants and contracts."""

    def test_invariant_has_unit_decomposition(self):
        """Invariant: '## Unit 1' in GOL_BLUEPRINT_CONTENT."""
        content = _get_md_content("GOL_BLUEPRINT_CONTENT")
        assert "## Unit 1" in content, \
            "GoL blueprint must have unit decomposition"

    def test_is_nonempty(self):
        """Content must be a substantial document."""
        content = _get_md_content("GOL_BLUEPRINT_CONTENT")
        assert len(content) > 50

    def test_is_markdown_with_units(self):
        """Blueprint should be markdown with unit sections."""
        content = _get_md_content("GOL_BLUEPRINT_CONTENT")
        assert "## Unit" in content


class TestGolProjectContextContent:
    """Verify GOL_PROJECT_CONTEXT_CONTENT invariants and contracts."""

    def test_invariant_references_game_of_life(self):
        """Invariant: 'Game of Life' in GOL_PROJECT_CONTEXT_CONTENT."""
        content = _get_md_content("GOL_PROJECT_CONTEXT_CONTENT")
        assert "Game of Life" in content, \
            "GoL context must reference Game of Life"

    def test_is_nonempty(self):
        """Content must be a substantial document."""
        content = _get_md_content("GOL_PROJECT_CONTEXT_CONTENT")
        assert len(content) > 50


# ===========================================================================
# 10. Cross-cutting: CLAUDE.md invariants (content consistency)
# ===========================================================================


class TestClaudeMdInvariants:
    """Verify that CLAUDE.md content (from both generate_claude_md and
    CLAUDE_MD_PY_CONTENT's render function) includes all required sections
    as specified in the blueprint invariants."""

    def test_generate_claude_md_run_routing_script(self, tmp_path):
        """CLAUDE.md must instruct: Run routing script on session start."""
        result = generate_claude_md("inv_test_proj", tmp_path)
        assert "routing" in result.lower()

    def test_generate_claude_md_execute_output(self, tmp_path):
        """CLAUDE.md must instruct: Execute routing script output exactly."""
        result = generate_claude_md("inv_test_proj", tmp_path)
        lower = result.lower()
        assert "execute" in lower or "run" in lower

    def test_generate_claude_md_verbatim_relay(self, tmp_path):
        """CLAUDE.md must instruct: Verbatim task prompt relay."""
        result = generate_claude_md("inv_test_proj", tmp_path)
        assert "verbatim" in result.lower()

    def test_generate_claude_md_no_improvise(self, tmp_path):
        """CLAUDE.md must instruct: Do not improvise pipeline flow."""
        result = generate_claude_md("inv_test_proj", tmp_path)
        assert "improvise" in result.lower()

    def test_generate_claude_md_defer_human_input(self, tmp_path):
        """CLAUDE.md must instruct: Defer human input during autonomous sequences."""
        result = generate_claude_md("inv_test_proj", tmp_path)
        lower = result.lower()
        assert "defer" in lower or "human input" in lower or "autonomous" in lower


# ===========================================================================
# 11. Additional edge case tests
# ===========================================================================


class TestEdgeCases:
    """Additional tests for edge cases and boundary conditions."""

    def test_generate_claude_md_with_special_chars_in_name(self, tmp_path):
        """Project name with hyphens, underscores should work."""
        # DATA ASSUMPTION: "my-project_v2.0" is a project name with
        # common special characters (hyphens, underscores, dots)
        result = generate_claude_md("my-project_v2.0", tmp_path)
        assert "my-project_v2.0" in result

    def test_generate_claude_md_with_long_name(self, tmp_path):
        """Project name can be longer than typical."""
        # DATA ASSUMPTION: A 50-character project name, representing an
        # unusually long but valid project name
        long_name = "a" * 50
        result = generate_claude_md(long_name, tmp_path)
        assert long_name in result

    def test_svp_config_json_is_parseable_to_matching_dict(self):
        """The config JSON, when parsed, should produce a dict matching
        Unit 1's DEFAULT_CONFIG in structure and values."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        # Verify it has the same top-level keys
        for key in UNIT_1_DEFAULT_CONFIG:
            assert key in parsed, f"Missing key from Unit 1 DEFAULT_CONFIG: {key}"

    def test_pipeline_state_json_matches_unit_2_structure(self):
        """The initial state JSON should have all fields from Unit 2's
        create_initial_state output."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        # Verify key fields from Unit 2's PipelineState schema
        expected_fields = [
            "stage", "sub_stage", "current_unit", "total_units",
            "fix_ladder_position", "red_run_retries", "alignment_iteration",
            "verified_units", "pass_history", "project_name",
        ]
        for field in expected_fields:
            assert field in parsed, f"Missing field from Unit 2 schema: {field}"

    def test_gol_stakeholder_spec_is_substantial_markdown(self):
        """GoL stakeholder spec should be a substantial markdown document."""
        content = _get_md_content("GOL_STAKEHOLDER_SPEC_CONTENT")
        # DATA ASSUMPTION: A real stakeholder spec is at least 500 characters
        assert len(content) > 500, \
            "GoL stakeholder spec should be a substantial document"

    def test_gol_blueprint_is_substantial_markdown(self):
        """GoL blueprint should be a substantial markdown document."""
        content = _get_md_content("GOL_BLUEPRINT_CONTENT")
        # DATA ASSUMPTION: A real blueprint is at least 500 characters
        assert len(content) > 500, \
            "GoL blueprint should be a substantial document"

    def test_gol_project_context_is_substantial(self):
        """GoL project context should be a substantial document."""
        content = _get_md_content("GOL_PROJECT_CONTEXT_CONTENT")
        # DATA ASSUMPTION: A project context is at least 200 characters
        assert len(content) > 200, \
            "GoL project context should be a substantial document"


# ===========================================================================
# 12. Coverage gap tests (added by coverage review)
# ===========================================================================


class TestCoverageGaps:
    """Tests added by coverage review to fill identified gaps in blueprint
    behavioral contract coverage.

    Synthetic Data Assumptions:
    ======================================================================
    DATA ASSUMPTION: "routing_proj", "section_proj", "skill_proj" are
    typical project name strings used for testing specific behavioral
    contracts of generate_claude_md output content.
    ======================================================================
    """

    # --- Gap 1: CLAUDE_MD_PY_CONTENT render function -- defer human input ---

    def test_render_function_includes_defer_human_input(self):
        """Contract: CLAUDE_MD_PY_CONTENT render function output must include
        defer human input instruction, matching the behavioral contract for
        generate_claude_md. The existing tests verify all other sections of
        the render function output but omit 'defer human input'."""
        content = _get_md_content("CLAUDE_MD_PY_CONTENT")
        namespace = {}
        exec(content, namespace)
        render_func = namespace["render_claude_md"]
        result = render_func("test_proj")
        lower_result = result.lower()
        assert "defer" in lower_result or "human input" in lower_result, \
            "render_claude_md output must include defer human input instruction"

    # --- Gap 2: generate_claude_md references routing script command ---

    def test_generate_claude_md_contains_routing_script_command(self, tmp_path):
        """Contract / Dependency (Unit 10): CLAUDE.md must reference the actual
        routing script command 'python scripts/routing.py'. The existing test
        only checks for the word 'routing' but not the full command."""
        # DATA ASSUMPTION: "routing_proj" is a typical project name
        result = generate_claude_md("routing_proj", tmp_path)
        assert "python scripts/routing.py" in result, \
            "CLAUDE.md must contain the routing script invocation command"

    # --- Gap 3: SVP_CONFIG_DEFAULT_JSON_CONTENT full dict equality ---

    def test_svp_config_content_full_equality_with_unit_1(self):
        """Contract: SVP_CONFIG_DEFAULT_JSON_CONTENT must match Unit 1
        DEFAULT_CONFIG exactly -- same keys and same values, no extra
        or missing keys. The existing test checks individual fields but
        does not verify there are no extra keys."""
        content = _get_md_content("SVP_CONFIG_DEFAULT_JSON_CONTENT")
        parsed = json.loads(content)
        assert parsed == UNIT_1_DEFAULT_CONFIG, \
            "SVP_CONFIG_DEFAULT_JSON_CONTENT must be exactly equal to Unit 1 DEFAULT_CONFIG"

    # --- Gap 4: README_SVP_TXT_CONTENT specifically mentions "two-layer" ---

    def test_readme_svp_mentions_two_layer(self):
        """Contract: README_SVP_TXT_CONTENT explains 'two-layer' write
        authorization, not just generic write authorization. The blueprint
        specifically says 'explains two-layer write authorization'."""
        content = _get_md_content("README_SVP_TXT_CONTENT")
        assert "two-layer" in content.lower(), \
            "README must specifically mention 'two-layer' write authorization"

    # --- Gap 5: PIPELINE_STATE debug_history and log_references fields ---

    def test_pipeline_state_debug_history_is_empty_list(self):
        """Contract: debug_history must be an empty list in initial state,
        consistent with Unit 2's create_initial_state output. The existing
        test_empty_lists only checks verified_units and pass_history."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert "debug_history" in parsed, \
            "Initial state must have debug_history field"
        assert parsed["debug_history"] == [], \
            "debug_history must be an empty list in initial state"

    def test_pipeline_state_log_references_is_empty_dict(self):
        """Contract: log_references must be an empty dict in initial state,
        consistent with Unit 2's create_initial_state output. This field
        was not verified by any existing test."""
        content = _get_md_content("PIPELINE_STATE_INITIAL_JSON_CONTENT")
        parsed = json.loads(content)
        assert "log_references" in parsed, \
            "Initial state must have log_references field"
        assert parsed["log_references"] == {}, \
            "log_references must be an empty dict in initial state"

    # --- Gap 6: generate_claude_md specific markdown section headings ---

    def test_generate_claude_md_has_session_start_section(self, tmp_path):
        """Contract: CLAUDE.md must have 'On Session Start' section heading
        to structure the routing script instruction. The existing tests check
        for content keywords but not section structure."""
        result = generate_claude_md("section_proj", tmp_path)
        assert "## On Session Start" in result, \
            "CLAUDE.md must have '## On Session Start' section"

    def test_generate_claude_md_has_six_step_section_heading(self, tmp_path):
        """Contract: CLAUDE.md must have a Six-Step Action Cycle section heading."""
        result = generate_claude_md("section_proj", tmp_path)
        assert "Six-Step Action Cycle" in result, \
            "CLAUDE.md must have 'Six-Step Action Cycle' in a section heading"

    def test_generate_claude_md_has_verbatim_section_heading(self, tmp_path):
        """Contract: CLAUDE.md must have a Verbatim Task Prompt Relay section heading."""
        result = generate_claude_md("section_proj", tmp_path)
        assert "Verbatim Task Prompt Relay" in result, \
            "CLAUDE.md must have 'Verbatim Task Prompt Relay' in a section heading"

    def test_generate_claude_md_has_do_not_improvise_section_heading(self, tmp_path):
        """Contract: CLAUDE.md must have a 'Do Not Improvise' section heading."""
        result = generate_claude_md("section_proj", tmp_path)
        assert "Do Not Improvise" in result, \
            "CLAUDE.md must have 'Do Not Improvise' in a section heading"

    def test_generate_claude_md_has_human_input_section_heading(self, tmp_path):
        """Contract: CLAUDE.md must have a 'Human Input During Autonomous Sequences'
        or similar section heading about deferring human input."""
        result = generate_claude_md("section_proj", tmp_path)
        assert "Human Input" in result, \
            "CLAUDE.md must have 'Human Input' in a section heading"

    def test_generate_claude_md_has_orchestration_skill_id(self, tmp_path):
        """Contract: CLAUDE.md must reference the orchestration skill identifier
        'svp-orchestration'. The existing test only checks for the word
        'orchestration' but not the specific skill ID."""
        result = generate_claude_md("skill_proj", tmp_path)
        assert "svp-orchestration" in result, \
            "CLAUDE.md must reference the 'svp-orchestration' skill identifier"
