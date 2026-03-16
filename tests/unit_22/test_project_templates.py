"""
Tests for Unit 22: Project Templates.

Verifies generate_claude_md function, template path
constants, and all content string constants.
"""

import json
from pathlib import Path

from src.unit_22.stub import (
    CLAUDE_MD_PY_CONTENT,
    DEFAULT_CONFIG_TEMPLATE,
    GOL_BLUEPRINT_CONTRACTS_CONTENT,
    GOL_BLUEPRINT_PROSE_CONTENT,
    GOL_PROJECT_CONTEXT_CONTENT,
    GOL_STAKEHOLDER_SPEC_CONTENT,
    INITIAL_STATE_TEMPLATE,
    PIPELINE_STATE_INITIAL_JSON_CONTENT,
    README_SVP_TEMPLATE,
    README_SVP_TXT_CONTENT,
    RUFF_CONFIG_TOML_CONTENT,
    SVP_CONFIG_DEFAULT_JSON_CONTENT,
    TOOLCHAIN_DEFAULT_JSON_CONTENT,
    TOOLCHAIN_DEFAULT_TEMPLATE,
    generate_claude_md,
)


class TestTemplatePaths:
    def test_default_config(self):
        assert DEFAULT_CONFIG_TEMPLATE == "templates/svp_config_default.json"

    def test_initial_state(self):
        assert INITIAL_STATE_TEMPLATE == "templates/pipeline_state_initial.json"

    def test_readme_svp(self):
        assert README_SVP_TEMPLATE == "templates/readme_svp.txt"

    def test_toolchain_default(self):
        expected = "toolchain_defaults/python_conda_pytest.json"
        assert TOOLCHAIN_DEFAULT_TEMPLATE == expected


class TestGenerateClaudeMd:
    def test_callable(self):
        assert callable(generate_claude_md)

    def test_returns_string(self):
        result = generate_claude_md("test_project", Path("/tmp/test"))
        assert isinstance(result, str)

    def test_contains_project_name(self):
        result = generate_claude_md("my_project", Path("/tmp/test"))
        assert "my_project" in result

    def test_contains_routing(self):
        result = generate_claude_md("test", Path("/tmp/test"))
        assert "routing" in result.lower()


class TestClaudeMdPyContent:
    def test_nonempty(self):
        assert isinstance(CLAUDE_MD_PY_CONTENT, str)
        assert len(CLAUDE_MD_PY_CONTENT) > 0

    def test_is_python(self):
        content = CLAUDE_MD_PY_CONTENT
        assert "def " in content or "import" in content


class TestSvpConfigDefaultJson:
    def test_nonempty(self):
        assert isinstance(SVP_CONFIG_DEFAULT_JSON_CONTENT, str)
        assert len(SVP_CONFIG_DEFAULT_JSON_CONTENT) > 0

    def test_valid_json(self):
        data = json.loads(SVP_CONFIG_DEFAULT_JSON_CONTENT)
        assert isinstance(data, dict)

    def test_has_iteration_limit(self):
        data = json.loads(SVP_CONFIG_DEFAULT_JSON_CONTENT)
        assert "iteration_limit" in data


class TestPipelineStateInitialJson:
    def test_nonempty(self):
        content = PIPELINE_STATE_INITIAL_JSON_CONTENT
        assert isinstance(content, str)
        assert len(content) > 0

    def test_valid_json(self):
        data = json.loads(PIPELINE_STATE_INITIAL_JSON_CONTENT)
        assert isinstance(data, dict)

    def test_has_delivered_repo_path(self):
        data = json.loads(PIPELINE_STATE_INITIAL_JSON_CONTENT)
        assert "delivered_repo_path" in data
        assert data["delivered_repo_path"] is None

    def test_has_redo_triggered_from(self):
        data = json.loads(PIPELINE_STATE_INITIAL_JSON_CONTENT)
        assert "redo_triggered_from" in data
        assert data["redo_triggered_from"] is None


class TestReadmeSvpTxt:
    def test_nonempty(self):
        assert isinstance(README_SVP_TXT_CONTENT, str)
        assert len(README_SVP_TXT_CONTENT) > 0

    def test_mentions_svp(self):
        assert "SVP" in README_SVP_TXT_CONTENT


class TestToolchainDefaultJson:
    def test_nonempty(self):
        content = TOOLCHAIN_DEFAULT_JSON_CONTENT
        assert isinstance(content, str)
        assert len(content) > 0

    def test_valid_json(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        assert isinstance(data, dict)

    def test_has_quality_section(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        assert "quality" in data

    def test_quality_has_gate_a(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        assert "gate_a" in data["quality"]

    def test_quality_has_gate_b(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        assert "gate_b" in data["quality"]

    def test_quality_has_gate_c(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        assert "gate_c" in data["quality"]

    def test_quality_has_packages(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        assert "packages" in data["quality"]

    def test_run_prefix_no_version_flags(self):
        data = json.loads(TOOLCHAIN_DEFAULT_JSON_CONTENT)
        prefix = data["environment"]["run_prefix"]
        assert "conda run -n {env_name}" in prefix
        assert "--no-banner" not in prefix


class TestRuffConfigToml:
    def test_nonempty(self):
        assert isinstance(RUFF_CONFIG_TOML_CONTENT, str)
        assert len(RUFF_CONFIG_TOML_CONTENT) > 0

    def test_has_line_length(self):
        assert "line-length" in RUFF_CONFIG_TOML_CONTENT


class TestGolExamples:
    def test_stakeholder_spec(self):
        assert isinstance(GOL_STAKEHOLDER_SPEC_CONTENT, str)
        assert len(GOL_STAKEHOLDER_SPEC_CONTENT) > 0

    def test_blueprint_prose(self):
        assert isinstance(GOL_BLUEPRINT_PROSE_CONTENT, str)
        assert len(GOL_BLUEPRINT_PROSE_CONTENT) > 0

    def test_blueprint_contracts(self):
        assert isinstance(GOL_BLUEPRINT_CONTRACTS_CONTENT, str)
        assert len(GOL_BLUEPRINT_CONTRACTS_CONTENT) > 0

    def test_project_context(self):
        assert isinstance(GOL_PROJECT_CONTEXT_CONTENT, str)
        assert len(GOL_PROJECT_CONTEXT_CONTENT) > 0
