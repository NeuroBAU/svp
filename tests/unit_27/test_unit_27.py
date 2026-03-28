"""
Tests for Unit 27: Project Templates.

Synthetic data assumptions:
- PYTHON_TOOLCHAIN is a dict with sections: "environment", "quality", "testing".
- R_TOOLCHAIN is a dict with the same top-level structure as PYTHON_TOOLCHAIN but
  with R-specific commands.
- PIPELINE_RUFF_TOML is a non-empty string containing ruff configuration with
  line-length=88 and target-version="py311".
- DELIVERY_QUALITY_TEMPLATES is a dict keyed by "python" and "r", each containing
  template strings with {{variable_name}} substitution syntax.
- render_template replaces all {{variable_name}} placeholders with values from a
  variables dict and raises ValueError on unresolved placeholders.
- Template variable names follow simple alphanumeric+underscore patterns.
"""

import pytest

from unit_27 import (
    DELIVERY_QUALITY_TEMPLATES,
    PIPELINE_RUFF_TOML,
    PYTHON_TOOLCHAIN,
    R_TOOLCHAIN,
    render_template,
)

# ---------------------------------------------------------------------------
# PYTHON_TOOLCHAIN structure tests
# ---------------------------------------------------------------------------


class TestPythonToolchainStructure:
    """Tests for the PYTHON_TOOLCHAIN constant (python_conda_pytest.json)."""

    def test_python_toolchain_is_a_dict(self):
        assert isinstance(PYTHON_TOOLCHAIN, dict)

    def test_python_toolchain_contains_environment_section(self):
        assert "environment" in PYTHON_TOOLCHAIN, (
            "PYTHON_TOOLCHAIN must contain an 'environment' section"
        )

    def test_python_toolchain_contains_quality_section(self):
        assert "quality" in PYTHON_TOOLCHAIN, (
            "PYTHON_TOOLCHAIN must contain a 'quality' section"
        )

    def test_python_toolchain_contains_testing_section(self):
        assert "testing" in PYTHON_TOOLCHAIN, (
            "PYTHON_TOOLCHAIN must contain a 'testing' section"
        )


class TestPythonToolchainEnvironment:
    """Tests for the environment section of PYTHON_TOOLCHAIN."""

    def test_environment_section_has_run_prefix(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "run_prefix" in env, "environment section must contain 'run_prefix'"

    def test_environment_section_has_create_command(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "create_command" in env, (
            "environment section must contain 'create_command'"
        )

    def test_environment_section_has_install_command(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "install_command" in env, (
            "environment section must contain 'install_command'"
        )

    def test_environment_section_has_cleanup_command(self):
        env = PYTHON_TOOLCHAIN["environment"]
        assert "cleanup_command" in env, (
            "environment section must contain 'cleanup_command'"
        )


class TestPythonToolchainQuality:
    """Tests for the quality section of PYTHON_TOOLCHAIN."""

    def test_quality_section_has_gate_a(self):
        quality = PYTHON_TOOLCHAIN["quality"]
        assert "gate_a" in quality, "quality section must contain 'gate_a'"

    def test_quality_section_has_gate_b(self):
        quality = PYTHON_TOOLCHAIN["quality"]
        assert "gate_b" in quality, "quality section must contain 'gate_b'"

    def test_quality_section_has_gate_c(self):
        quality = PYTHON_TOOLCHAIN["quality"]
        assert "gate_c" in quality, "quality section must contain 'gate_c'"

    def test_gate_a_is_format_plus_light_lint_composition(self):
        """gate_a should be a composition of format + light lint steps."""
        gate_a = PYTHON_TOOLCHAIN["quality"]["gate_a"]
        # Gate compositions are expected to be lists or similar structured data
        assert gate_a is not None, "gate_a must not be None"

    def test_gate_b_is_format_plus_heavy_lint_plus_type_check_composition(self):
        """gate_b should be a composition of format + heavy lint + type check."""
        gate_b = PYTHON_TOOLCHAIN["quality"]["gate_b"]
        assert gate_b is not None, "gate_b must not be None"

    def test_gate_c_is_full_project_check_composition(self):
        """gate_c should be a full project check composition."""
        gate_c = PYTHON_TOOLCHAIN["quality"]["gate_c"]
        assert gate_c is not None, "gate_c must not be None"


class TestPythonToolchainTesting:
    """Tests for the testing section of PYTHON_TOOLCHAIN."""

    def test_testing_section_has_run_command(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "run_command" in testing, "testing section must contain 'run_command'"

    def test_testing_section_has_collection_error_indicators(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "collection_error_indicators" in testing, (
            "testing section must contain 'collection_error_indicators'"
        )

    def test_testing_section_has_unit_flags(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "unit_flags" in testing, "testing section must contain 'unit_flags'"

    def test_testing_section_has_project_flags(self):
        testing = PYTHON_TOOLCHAIN["testing"]
        assert "project_flags" in testing, (
            "testing section must contain 'project_flags'"
        )


# ---------------------------------------------------------------------------
# R_TOOLCHAIN structure tests
# ---------------------------------------------------------------------------


class TestRToolchainStructure:
    """Tests for the R_TOOLCHAIN constant (r_renv_testthat.json)."""

    def test_r_toolchain_is_a_dict(self):
        assert isinstance(R_TOOLCHAIN, dict)

    def test_r_toolchain_contains_environment_section(self):
        assert "environment" in R_TOOLCHAIN, (
            "R_TOOLCHAIN must contain an 'environment' section"
        )

    def test_r_toolchain_contains_quality_section(self):
        assert "quality" in R_TOOLCHAIN, "R_TOOLCHAIN must contain a 'quality' section"

    def test_r_toolchain_contains_testing_section(self):
        assert "testing" in R_TOOLCHAIN, "R_TOOLCHAIN must contain a 'testing' section"


class TestRToolchainEnvironment:
    """Tests for the environment section of R_TOOLCHAIN."""

    def test_environment_section_has_run_prefix(self):
        env = R_TOOLCHAIN["environment"]
        assert "run_prefix" in env

    def test_environment_section_has_create_command(self):
        env = R_TOOLCHAIN["environment"]
        assert "create_command" in env

    def test_environment_section_has_install_command(self):
        env = R_TOOLCHAIN["environment"]
        assert "install_command" in env

    def test_environment_section_has_cleanup_command(self):
        env = R_TOOLCHAIN["environment"]
        assert "cleanup_command" in env


class TestRToolchainQuality:
    """Tests for the quality section of R_TOOLCHAIN."""

    def test_quality_section_has_gate_a(self):
        quality = R_TOOLCHAIN["quality"]
        assert "gate_a" in quality

    def test_quality_section_has_gate_b(self):
        quality = R_TOOLCHAIN["quality"]
        assert "gate_b" in quality

    def test_quality_section_has_gate_c(self):
        quality = R_TOOLCHAIN["quality"]
        assert "gate_c" in quality

    def test_r_gates_use_lintr_and_styler(self):
        """R gate compositions should reference lintr and/or styler tools."""
        quality = R_TOOLCHAIN["quality"]
        # Serialize the quality section to check for R-specific tool references
        quality_str = str(quality).lower()
        assert "lintr" in quality_str or "styler" in quality_str, (
            "R quality gates must reference lintr and/or styler"
        )

    def test_r_type_checker_is_none(self):
        """R toolchain should have no type checker (tool: 'none')."""
        quality = R_TOOLCHAIN["quality"]
        quality_str = str(quality).lower()
        # At least one gate should indicate type checker is "none"
        # The blueprint says "No type checker (tool: 'none')"
        # We verify this by checking the gate_b or quality section does not
        # reference a real type checker tool like mypy/pyright
        assert "mypy" not in quality_str, (
            "R toolchain must not reference mypy type checker"
        )
        assert "pyright" not in quality_str, (
            "R toolchain must not reference pyright type checker"
        )


class TestRToolchainTesting:
    """Tests for the testing section of R_TOOLCHAIN."""

    def test_testing_section_has_run_command(self):
        testing = R_TOOLCHAIN["testing"]
        assert "run_command" in testing

    def test_testing_section_has_collection_error_indicators(self):
        testing = R_TOOLCHAIN["testing"]
        assert "collection_error_indicators" in testing

    def test_testing_section_has_unit_flags(self):
        testing = R_TOOLCHAIN["testing"]
        assert "unit_flags" in testing

    def test_testing_section_has_project_flags(self):
        testing = R_TOOLCHAIN["testing"]
        assert "project_flags" in testing


class TestToolchainStructuralParity:
    """R_TOOLCHAIN should have the same top-level structure as PYTHON_TOOLCHAIN."""

    def test_same_top_level_keys(self):
        python_keys = set(PYTHON_TOOLCHAIN.keys())
        r_keys = set(R_TOOLCHAIN.keys())
        # Both must have at least environment, quality, testing
        required = {"environment", "quality", "testing"}
        assert required.issubset(python_keys), (
            f"PYTHON_TOOLCHAIN missing required keys: {required - python_keys}"
        )
        assert required.issubset(r_keys), (
            f"R_TOOLCHAIN missing required keys: {required - r_keys}"
        )

    def test_environment_sections_have_same_keys(self):
        python_env_keys = set(PYTHON_TOOLCHAIN["environment"].keys())
        r_env_keys = set(R_TOOLCHAIN["environment"].keys())
        required_env_keys = {
            "run_prefix",
            "create_command",
            "install_command",
            "cleanup_command",
        }
        assert required_env_keys.issubset(python_env_keys)
        assert required_env_keys.issubset(r_env_keys)

    def test_testing_sections_have_same_keys(self):
        python_test_keys = set(PYTHON_TOOLCHAIN["testing"].keys())
        r_test_keys = set(R_TOOLCHAIN["testing"].keys())
        required_test_keys = {
            "run_command",
            "collection_error_indicators",
            "unit_flags",
            "project_flags",
        }
        assert required_test_keys.issubset(python_test_keys)
        assert required_test_keys.issubset(r_test_keys)

    def test_quality_sections_have_same_gate_keys(self):
        python_quality_keys = set(PYTHON_TOOLCHAIN["quality"].keys())
        r_quality_keys = set(R_TOOLCHAIN["quality"].keys())
        required_gate_keys = {"gate_a", "gate_b", "gate_c"}
        assert required_gate_keys.issubset(python_quality_keys)
        assert required_gate_keys.issubset(r_quality_keys)


# ---------------------------------------------------------------------------
# PIPELINE_RUFF_TOML tests
# ---------------------------------------------------------------------------


class TestPipelineRuffToml:
    """Tests for the PIPELINE_RUFF_TOML constant."""

    def test_pipeline_ruff_toml_is_a_string(self):
        assert isinstance(PIPELINE_RUFF_TOML, str)

    def test_pipeline_ruff_toml_is_not_empty(self):
        assert len(PIPELINE_RUFF_TOML.strip()) > 0, (
            "PIPELINE_RUFF_TOML must not be empty"
        )

    def test_pipeline_ruff_toml_specifies_line_length_88(self):
        assert "88" in PIPELINE_RUFF_TOML, (
            "PIPELINE_RUFF_TOML must specify line-length = 88"
        )

    def test_pipeline_ruff_toml_specifies_target_version_py311(self):
        assert "py311" in PIPELINE_RUFF_TOML, (
            "PIPELINE_RUFF_TOML must specify target-version = 'py311'"
        )

    def test_pipeline_ruff_toml_contains_line_length_directive(self):
        """Verify the line-length directive is present as a TOML key."""
        assert "line-length" in PIPELINE_RUFF_TOML, (
            "PIPELINE_RUFF_TOML must contain a 'line-length' directive"
        )

    def test_pipeline_ruff_toml_contains_target_version_directive(self):
        """Verify the target-version directive is present as a TOML key."""
        assert "target-version" in PIPELINE_RUFF_TOML, (
            "PIPELINE_RUFF_TOML must contain a 'target-version' directive"
        )


# ---------------------------------------------------------------------------
# DELIVERY_QUALITY_TEMPLATES tests
# ---------------------------------------------------------------------------


class TestDeliveryQualityTemplatesStructure:
    """Tests for the DELIVERY_QUALITY_TEMPLATES constant."""

    def test_delivery_quality_templates_is_a_dict(self):
        assert isinstance(DELIVERY_QUALITY_TEMPLATES, dict)

    def test_delivery_quality_templates_has_python_key(self):
        assert "python" in DELIVERY_QUALITY_TEMPLATES, (
            "DELIVERY_QUALITY_TEMPLATES must contain a 'python' key"
        )

    def test_delivery_quality_templates_has_r_key(self):
        assert "r" in DELIVERY_QUALITY_TEMPLATES, (
            "DELIVERY_QUALITY_TEMPLATES must contain an 'r' key"
        )


class TestDeliveryQualityTemplatesPython:
    """Tests for the Python section of DELIVERY_QUALITY_TEMPLATES."""

    def test_python_templates_has_ruff_toml_template(self):
        python_templates = DELIVERY_QUALITY_TEMPLATES["python"]
        assert "ruff.toml.template" in python_templates, (
            "Python templates must contain 'ruff.toml.template'"
        )

    def test_python_templates_has_flake8_template(self):
        python_templates = DELIVERY_QUALITY_TEMPLATES["python"]
        assert "flake8.template" in python_templates, (
            "Python templates must contain 'flake8.template'"
        )

    def test_python_templates_has_mypy_ini_template(self):
        python_templates = DELIVERY_QUALITY_TEMPLATES["python"]
        assert "mypy.ini.template" in python_templates, (
            "Python templates must contain 'mypy.ini.template'"
        )

    def test_python_templates_has_pyproject_black_toml_template(self):
        python_templates = DELIVERY_QUALITY_TEMPLATES["python"]
        assert "pyproject_black.toml.template" in python_templates, (
            "Python templates must contain 'pyproject_black.toml.template'"
        )

    def test_python_templates_values_are_strings(self):
        python_templates = DELIVERY_QUALITY_TEMPLATES["python"]
        for key, value in python_templates.items():
            assert isinstance(value, str), (
                f"Python template '{key}' value must be a string, got {type(value)}"
            )


class TestDeliveryQualityTemplatesR:
    """Tests for the R section of DELIVERY_QUALITY_TEMPLATES."""

    def test_r_templates_has_lintr_template(self):
        r_templates = DELIVERY_QUALITY_TEMPLATES["r"]
        assert "lintr.template" in r_templates, (
            "R templates must contain 'lintr.template'"
        )

    def test_r_templates_has_styler_template(self):
        r_templates = DELIVERY_QUALITY_TEMPLATES["r"]
        assert "styler.template" in r_templates, (
            "R templates must contain 'styler.template'"
        )

    def test_r_templates_values_are_strings(self):
        r_templates = DELIVERY_QUALITY_TEMPLATES["r"]
        for key, value in r_templates.items():
            assert isinstance(value, str), (
                f"R template '{key}' value must be a string, got {type(value)}"
            )


class TestDeliveryQualityTemplatesSubstitutionSyntax:
    """Templates use {{variable_name}} substitution syntax."""

    def test_at_least_one_python_template_uses_double_brace_syntax(self):
        """At least one Python template should contain {{...}} placeholders."""
        python_templates = DELIVERY_QUALITY_TEMPLATES["python"]
        has_placeholder = False
        for value in python_templates.values():
            if "{{" in value and "}}" in value:
                has_placeholder = True
                break
        assert has_placeholder, (
            "At least one Python template must use {{variable_name}} syntax"
        )

    def test_at_least_one_r_template_uses_double_brace_syntax(self):
        """At least one R template should contain {{...}} placeholders."""
        r_templates = DELIVERY_QUALITY_TEMPLATES["r"]
        has_placeholder = False
        for value in r_templates.values():
            if "{{" in value and "}}" in value:
                has_placeholder = True
                break
        assert has_placeholder, (
            "At least one R template must use {{variable_name}} syntax"
        )


# ---------------------------------------------------------------------------
# render_template tests
# ---------------------------------------------------------------------------


class TestRenderTemplateBasicSubstitution:
    """Tests for render_template basic variable substitution."""

    def test_replaces_single_variable(self):
        template = "line_length = {{line_length}}"
        result = render_template(template, {"line_length": "88"})
        assert result == "line_length = 88"

    def test_replaces_multiple_variables(self):
        template = "name={{name}}, version={{version}}"
        result = render_template(template, {"name": "myproject", "version": "1.0"})
        assert result == "name=myproject, version=1.0"

    def test_replaces_same_variable_multiple_times(self):
        template = "{{x}} and {{x}} again"
        result = render_template(template, {"x": "hello"})
        assert result == "hello and hello again"

    def test_preserves_text_without_placeholders(self):
        template = "no placeholders here"
        result = render_template(template, {})
        assert result == "no placeholders here"

    def test_handles_empty_template_string(self):
        result = render_template("", {})
        assert result == ""

    def test_replaces_variable_with_empty_string_value(self):
        template = "prefix_{{var}}_suffix"
        result = render_template(template, {"var": ""})
        assert result == "prefix__suffix"

    def test_handles_multiline_template(self):
        template = "line1={{a}}\nline2={{b}}\nline3={{c}}"
        result = render_template(
            template,
            {"a": "val1", "b": "val2", "c": "val3"},
        )
        assert result == "line1=val1\nline2=val2\nline3=val3"

    def test_replaces_adjacent_variables(self):
        template = "{{first}}{{second}}"
        result = render_template(template, {"first": "hello", "second": "world"})
        assert result == "helloworld"


class TestRenderTemplateUnresolvedPlaceholders:
    """Tests for render_template error handling on unresolved placeholders."""

    def test_raises_value_error_for_single_unresolved_placeholder(self):
        template = "value={{missing}}"
        with pytest.raises(ValueError):
            render_template(template, {})

    def test_raises_value_error_when_some_placeholders_unresolved(self):
        template = "{{resolved}} and {{unresolved}}"
        with pytest.raises(ValueError):
            render_template(template, {"resolved": "ok"})

    def test_raises_value_error_for_unresolved_even_with_extra_variables(self):
        """Extra variables in dict should not mask unresolved placeholders."""
        template = "{{needed}}"
        with pytest.raises(ValueError):
            render_template(template, {"not_needed": "value"})

    def test_does_not_raise_when_all_placeholders_resolved(self):
        template = "{{a}} and {{b}}"
        # Should not raise
        result = render_template(template, {"a": "x", "b": "y"})
        assert result == "x and y"

    def test_extra_variables_do_not_cause_error(self):
        """Variables dict may contain keys not present in the template."""
        template = "value={{x}}"
        result = render_template(template, {"x": "1", "y": "2", "z": "3"})
        assert result == "value=1"


class TestRenderTemplateEdgeCases:
    """Edge case tests for render_template."""

    def test_variable_name_with_underscores(self):
        template = "{{my_long_variable_name}}"
        result = render_template(template, {"my_long_variable_name": "val"})
        assert result == "val"

    def test_variable_name_with_digits(self):
        template = "{{var123}}"
        result = render_template(template, {"var123": "numeric"})
        assert result == "numeric"

    def test_variable_value_containing_braces(self):
        """Variable values that look like placeholders should be literal."""
        template = "{{var}}"
        result = render_template(template, {"var": "{{not_a_var}}"})
        # The result should contain the literal text, not trigger another substitution
        assert "not_a_var" in result

    def test_preserves_single_braces(self):
        """Single braces {like_this} should not be treated as placeholders."""
        template = "{single} and {{double}}"
        result = render_template(template, {"double": "replaced"})
        assert "{single}" in result
        assert "replaced" in result

    def test_whitespace_in_template_preserved(self):
        template = "  {{var}}  "
        result = render_template(template, {"var": "x"})
        assert result == "  x  "

    def test_template_with_only_a_placeholder(self):
        template = "{{only}}"
        result = render_template(template, {"only": "value"})
        assert result == "value"


class TestRenderTemplateIntegrationWithDeliveryTemplates:
    """Test render_template with actual DELIVERY_QUALITY_TEMPLATES content."""

    def test_can_render_python_ruff_template_without_error(self):
        """Verify render_template works with a real Python ruff template."""
        python_templates = DELIVERY_QUALITY_TEMPLATES.get("python", {})
        ruff_template = python_templates.get("ruff.toml.template", "")
        if not ruff_template:
            pytest.skip("ruff.toml.template is empty in stub")

        # Extract all placeholder names from the template
        import re

        placeholders = set(re.findall(r"\{\{(\w+)\}\}", ruff_template))
        # Build a variables dict with synthetic values for each placeholder
        variables = {name: "test_value" for name in placeholders}
        # Should not raise
        result = render_template(ruff_template, variables)
        assert "{{" not in result, "All placeholders should be resolved after rendering"

    def test_can_render_r_lintr_template_without_error(self):
        """Verify render_template works with a real R lintr template."""
        r_templates = DELIVERY_QUALITY_TEMPLATES.get("r", {})
        lintr_template = r_templates.get("lintr.template", "")
        if not lintr_template:
            pytest.skip("lintr.template is empty in stub")

        import re

        placeholders = set(re.findall(r"\{\{(\w+)\}\}", lintr_template))
        variables = {name: "test_value" for name in placeholders}
        result = render_template(lintr_template, variables)
        assert "{{" not in result


# ---------------------------------------------------------------------------
# R_TOOLCHAIN vs PYTHON_TOOLCHAIN R-specific command differences
# ---------------------------------------------------------------------------


class TestRToolchainUsesRSpecificCommands:
    """R_TOOLCHAIN should contain R-specific commands, not Python ones."""

    def test_r_environment_commands_are_not_python_commands(self):
        r_env = R_TOOLCHAIN["environment"]
        python_env = PYTHON_TOOLCHAIN["environment"]
        # run_prefix should differ between Python and R
        assert r_env["run_prefix"] != python_env["run_prefix"], (
            "R run_prefix should differ from Python run_prefix"
        )

    def test_r_testing_run_command_differs_from_python(self):
        r_testing = R_TOOLCHAIN["testing"]
        python_testing = PYTHON_TOOLCHAIN["testing"]
        assert r_testing["run_command"] != python_testing["run_command"], (
            "R testing run_command should differ from Python testing run_command"
        )


# ---------------------------------------------------------------------------
# Type invariant tests
# ---------------------------------------------------------------------------


class TestTypeInvariants:
    """Verify that all module-level constants have correct types."""

    def test_python_toolchain_type(self):
        assert isinstance(PYTHON_TOOLCHAIN, dict)

    def test_r_toolchain_type(self):
        assert isinstance(R_TOOLCHAIN, dict)

    def test_pipeline_ruff_toml_type(self):
        assert isinstance(PIPELINE_RUFF_TOML, str)

    def test_delivery_quality_templates_type(self):
        assert isinstance(DELIVERY_QUALITY_TEMPLATES, dict)

    def test_python_toolchain_environment_is_dict(self):
        assert isinstance(PYTHON_TOOLCHAIN.get("environment"), dict)

    def test_python_toolchain_quality_is_dict(self):
        assert isinstance(PYTHON_TOOLCHAIN.get("quality"), dict)

    def test_python_toolchain_testing_is_dict(self):
        assert isinstance(PYTHON_TOOLCHAIN.get("testing"), dict)

    def test_r_toolchain_environment_is_dict(self):
        assert isinstance(R_TOOLCHAIN.get("environment"), dict)

    def test_r_toolchain_quality_is_dict(self):
        assert isinstance(R_TOOLCHAIN.get("quality"), dict)

    def test_r_toolchain_testing_is_dict(self):
        assert isinstance(R_TOOLCHAIN.get("testing"), dict)

    def test_delivery_quality_templates_python_is_dict(self):
        assert isinstance(DELIVERY_QUALITY_TEMPLATES.get("python"), dict)

    def test_delivery_quality_templates_r_is_dict(self):
        assert isinstance(DELIVERY_QUALITY_TEMPLATES.get("r"), dict)

    def test_render_template_returns_string(self):
        result = render_template("hello", {})
        assert isinstance(result, str)


class TestRenderTemplateCallableSignature:
    """Verify render_template accepts the documented signature."""

    def test_accepts_str_and_dict_arguments(self):
        """render_template(template_content: str, variables: Dict[str, str]) -> str."""
        result = render_template("text", {})
        assert isinstance(result, str)

    def test_accepts_non_empty_variables_dict(self):
        result = render_template("{{k}}", {"k": "v"})
        assert isinstance(result, str)
        assert result == "v"
