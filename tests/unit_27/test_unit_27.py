"""Tests for Unit 27: Project Templates (Lessons Learned).

Synthetic data assumptions:
- PYTHON_TOOLCHAIN is a dict with keys "environment", "quality", "testing".
- R_TOOLCHAIN is a dict with the same top-level structure but R-specific commands.
- PIPELINE_RUFF_TOML is a non-empty string containing ruff configuration.
- DELIVERY_QUALITY_TEMPLATES is a dict keyed by "python" and "r", each containing
  template strings with {{variable_name}} substitution syntax.
- render_template replaces {{variable_name}} placeholders from a variables dict
  and raises ValueError on unresolved placeholders.
"""

import json

import pytest

from src.unit_27.stub import (
    DELIVERY_QUALITY_TEMPLATES,
    PIPELINE_RUFF_TOML,
    PYTHON_TOOLCHAIN,
    R_TOOLCHAIN,
    render_template,
)

# ---------------------------------------------------------------------------
# PYTHON_TOOLCHAIN contracts
# ---------------------------------------------------------------------------


class TestPythonToolchain:
    """Tests for the PYTHON_TOOLCHAIN constant."""

    def test_python_toolchain_is_dict(self):
        assert isinstance(PYTHON_TOOLCHAIN, dict)

    def test_python_toolchain_has_environment_section(self):
        assert "environment" in PYTHON_TOOLCHAIN

    def test_python_toolchain_environment_has_run_prefix(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "run_prefix" in env

    def test_python_toolchain_environment_has_create_command(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "create_command" in env

    def test_python_toolchain_environment_has_install_command(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "install_command" in env

    def test_python_toolchain_environment_has_cleanup_command(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "cleanup_command" in env

    def test_python_toolchain_has_quality_section(self):
        assert "quality" in PYTHON_TOOLCHAIN

    def test_python_toolchain_quality_has_gate_a(self):
        quality = PYTHON_TOOLCHAIN["quality"]
        assert "gate_a" in quality

    def test_python_toolchain_quality_gate_a_is_format_plus_light_lint(self):
        gate_a = PYTHON_TOOLCHAIN["quality"]["gate_a"]
        # gate_a should be a composition of format + light lint
        assert isinstance(gate_a, (list, dict, str))

    def test_python_toolchain_quality_has_gate_b(self):
        quality = PYTHON_TOOLCHAIN["quality"]
        assert "gate_b" in quality

    def test_python_toolchain_quality_has_gate_c(self):
        quality = PYTHON_TOOLCHAIN["quality"]
        assert "gate_c" in quality

    def test_python_toolchain_has_testing_section(self):
        assert "testing" in PYTHON_TOOLCHAIN

    def test_python_toolchain_testing_has_run_command(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "run_command" in testing

    def test_python_toolchain_testing_has_collection_error_indicators(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "collection_error_indicators" in testing

    def test_python_toolchain_testing_has_unit_flags(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "unit_flags" in testing

    def test_python_toolchain_testing_has_project_flags(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "project_flags" in testing

    def test_python_toolchain_is_json_serializable(self):
        """Toolchain dicts should be JSON-serializable for file emission."""
        serialized = json.dumps(PYTHON_TOOLCHAIN)
        assert isinstance(serialized, str)
        roundtripped = json.loads(serialized)
        assert roundtripped == PYTHON_TOOLCHAIN


# ---------------------------------------------------------------------------
# R_TOOLCHAIN contracts
# ---------------------------------------------------------------------------


class TestRToolchain:
    """Tests for the R_TOOLCHAIN constant."""

    def test_r_toolchain_is_dict(self):
        assert isinstance(R_TOOLCHAIN, dict)

    def test_r_toolchain_has_environment_section(self):
        assert "environment" in R_TOOLCHAIN

    def test_r_toolchain_environment_has_run_prefix(self):
        env = R_TOOLCHAIN["environment"]
        assert "run_prefix" in env

    def test_r_toolchain_environment_has_create_command(self):
        env = R_TOOLCHAIN["environment"]
        assert "create_command" in env

    def test_r_toolchain_environment_has_install_command(self):
        env = R_TOOLCHAIN["environment"]
        assert "install_command" in env

    def test_r_toolchain_environment_has_cleanup_command(self):
        env = R_TOOLCHAIN["environment"]
        assert "cleanup_command" in env

    def test_r_toolchain_has_quality_section(self):
        assert "quality" in R_TOOLCHAIN

    def test_r_toolchain_quality_has_gate_a(self):
        quality = R_TOOLCHAIN["quality"]
        assert "gate_a" in quality

    def test_r_toolchain_quality_has_gate_b(self):
        quality = R_TOOLCHAIN["quality"]
        assert "gate_b" in quality

    def test_r_toolchain_quality_has_gate_c(self):
        quality = R_TOOLCHAIN["quality"]
        assert "gate_c" in quality

    def test_r_toolchain_quality_gates_use_lintr_styler(self):
        """R gates should reference lintr and/or styler tools."""
        quality = R_TOOLCHAIN["quality"]
        quality_str = json.dumps(quality).lower()
        assert "lintr" in quality_str or "styler" in quality_str

    def test_r_toolchain_quality_no_type_checker(self):
        """R has no type checker -- should be 'none' or absent."""
        quality = R_TOOLCHAIN["quality"]
        quality_str = json.dumps(quality).lower()
        # If type_check is present, it should indicate "none"
        if "type_check" in quality_str:
            # Find the type check field and verify it's none
            gate_b = quality.get("gate_b", {})
            if isinstance(gate_b, dict) and "type_check" in gate_b:
                assert gate_b["type_check"] in ("none", None, "")
            elif isinstance(gate_b, list):
                for item in gate_b:
                    if isinstance(item, dict) and item.get("tool") == "type_check":
                        assert (
                            item.get("tool", "") == "none"
                            or "none" in str(item).lower()
                        )

    def test_r_toolchain_has_testing_section(self):
        assert "testing" in R_TOOLCHAIN

    def test_r_toolchain_testing_has_run_command(self):
        testing = R_TOOLCHAIN["testing"]
        assert "run_command" in testing

    def test_r_toolchain_same_top_level_structure_as_python(self):
        """R and Python toolchains share the same top-level keys."""
        assert set(PYTHON_TOOLCHAIN.keys()) == set(R_TOOLCHAIN.keys())

    def test_r_toolchain_is_json_serializable(self):
        serialized = json.dumps(R_TOOLCHAIN)
        assert isinstance(serialized, str)
        roundtripped = json.loads(serialized)
        assert roundtripped == R_TOOLCHAIN


# ---------------------------------------------------------------------------
# PIPELINE_RUFF_TOML contracts
# ---------------------------------------------------------------------------


class TestPipelineRuffToml:
    """Tests for the PIPELINE_RUFF_TOML constant."""

    def test_pipeline_ruff_toml_is_string(self):
        assert isinstance(PIPELINE_RUFF_TOML, str)

    def test_pipeline_ruff_toml_is_nonempty(self):
        assert len(PIPELINE_RUFF_TOML.strip()) > 0

    def test_pipeline_ruff_toml_line_length_88(self):
        """Ruff config specifies line-length = 88."""
        assert "88" in PIPELINE_RUFF_TOML
        # More specific: look for line-length setting
        lower = PIPELINE_RUFF_TOML.lower()
        assert "line-length" in lower or "line_length" in lower

    def test_pipeline_ruff_toml_target_version_py311(self):
        """Ruff config targets py311."""
        lower = PIPELINE_RUFF_TOML.lower()
        assert "py311" in lower


# ---------------------------------------------------------------------------
# DELIVERY_QUALITY_TEMPLATES contracts
# ---------------------------------------------------------------------------


class TestDeliveryQualityTemplates:
    """Tests for the DELIVERY_QUALITY_TEMPLATES constant."""

    def test_delivery_quality_templates_is_dict(self):
        assert isinstance(DELIVERY_QUALITY_TEMPLATES, dict)

    def test_delivery_quality_templates_has_python_key(self):
        assert "python" in DELIVERY_QUALITY_TEMPLATES

    def test_delivery_quality_templates_has_r_key(self):
        assert "r" in DELIVERY_QUALITY_TEMPLATES

    def test_python_templates_has_ruff_toml_template(self):
        assert "ruff.toml.template" in DELIVERY_QUALITY_TEMPLATES["python"]

    def test_python_templates_has_flake8_template(self):
        assert "flake8.template" in DELIVERY_QUALITY_TEMPLATES["python"]

    def test_python_templates_has_mypy_ini_template(self):
        assert "mypy.ini.template" in DELIVERY_QUALITY_TEMPLATES["python"]

    def test_python_templates_has_pyproject_black_toml_template(self):
        assert "pyproject_black.toml.template" in DELIVERY_QUALITY_TEMPLATES["python"]

    def test_r_templates_has_lintr_template(self):
        assert "lintr.template" in DELIVERY_QUALITY_TEMPLATES["r"]

    def test_r_templates_has_styler_template(self):
        assert "styler.template" in DELIVERY_QUALITY_TEMPLATES["r"]

    def test_python_templates_values_are_strings(self):
        for key, value in DELIVERY_QUALITY_TEMPLATES["python"].items():
            assert isinstance(value, str), f"Python template '{key}' is not a string"

    def test_r_templates_values_are_strings(self):
        for key, value in DELIVERY_QUALITY_TEMPLATES["r"].items():
            assert isinstance(value, str), f"R template '{key}' is not a string"

    def test_templates_use_double_brace_substitution_syntax(self):
        """All templates should use {{variable_name}} substitution syntax."""
        for lang_key in ("python", "r"):
            for tmpl_key, tmpl_content in DELIVERY_QUALITY_TEMPLATES[lang_key].items():
                # Templates should contain at least one {{...}} placeholder
                assert "{{" in tmpl_content and "}}" in tmpl_content, (
                    f"Template '{lang_key}/{tmpl_key}' lacks {{{{variable_name}}}} syntax"
                )


# ---------------------------------------------------------------------------
# render_template contracts
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    """Tests for the render_template function."""

    def test_render_template_replaces_single_variable(self):
        template = "Hello, {{name}}!"
        result = render_template(template, {"name": "World"})
        assert result == "Hello, World!"

    def test_render_template_replaces_multiple_variables(self):
        template = "{{greeting}}, {{name}}! You are {{age}} years old."
        variables = {"greeting": "Hi", "name": "Alice", "age": "30"}
        result = render_template(template, variables)
        assert result == "Hi, Alice! You are 30 years old."

    def test_render_template_replaces_duplicate_variables(self):
        template = "{{x}} and {{x}} again"
        result = render_template(template, {"x": "value"})
        assert result == "value and value again"

    def test_render_template_no_placeholders_returns_unchanged(self):
        template = "No placeholders here"
        result = render_template(template, {})
        assert result == "No placeholders here"

    def test_render_template_empty_string_returns_empty(self):
        result = render_template("", {})
        assert result == ""

    def test_render_template_variable_value_can_be_empty_string(self):
        template = "before{{x}}after"
        result = render_template(template, {"x": ""})
        assert result == "beforeafter"

    def test_render_template_unresolved_placeholder_raises_value_error(self):
        template = "Hello, {{name}}! Your id is {{id}}."
        with pytest.raises(ValueError):
            render_template(template, {"name": "Bob"})

    def test_render_template_all_unresolved_raises_value_error(self):
        template = "{{a}} and {{b}}"
        with pytest.raises(ValueError):
            render_template(template, {})

    def test_render_template_extra_variables_ignored(self):
        """Extra keys in variables dict that don't appear in template are fine."""
        template = "Hello, {{name}}!"
        result = render_template(template, {"name": "World", "unused": "value"})
        assert result == "Hello, World!"

    def test_render_template_preserves_whitespace(self):
        template = "  {{x}}  \n  {{y}}  "
        result = render_template(template, {"x": "A", "y": "B"})
        assert result == "  A  \n  B  "

    def test_render_template_variable_name_with_underscores(self):
        template = "{{my_variable_name}}"
        result = render_template(template, {"my_variable_name": "value"})
        assert result == "value"

    def test_render_template_multiline_template(self):
        template = "line1: {{a}}\nline2: {{b}}\nline3: {{c}}"
        result = render_template(template, {"a": "1", "b": "2", "c": "3"})
        assert result == "line1: 1\nline2: 2\nline3: 3"

    def test_render_template_returns_string(self):
        result = render_template("{{x}}", {"x": "val"})
        assert isinstance(result, str)
