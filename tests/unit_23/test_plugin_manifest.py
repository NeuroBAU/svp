"""
Tests for Unit 23: Plugin Manifest and Structural
Validation.

Verifies PLUGIN_JSON, MARKETPLACE_JSON dicts, content
strings, validate_plugin_structure, compliance scan
functions.
"""

import json

from src.unit_23.stub import (
    MARKETPLACE_JSON,
    MARKETPLACE_JSON_CONTENT,
    PLUGIN_JSON,
    PLUGIN_JSON_CONTENT,
    _get_banned_patterns,
    _scan_file_ast,
    compliance_scan_main,
    run_compliance_scan,
    validate_plugin_structure,
)


class TestPluginJson:
    def test_name(self):
        assert PLUGIN_JSON["name"] == "svp"

    def test_version(self):
        assert PLUGIN_JSON["version"] == "2.1.0"

    def test_description(self):
        assert "Stratified Verification" in (PLUGIN_JSON["description"])


class TestMarketplaceJson:
    def test_name(self):
        assert MARKETPLACE_JSON["name"] == "svp"

    def test_owner(self):
        assert MARKETPLACE_JSON["owner"]["name"] == "SVP"

    def test_plugins_list(self):
        plugins = MARKETPLACE_JSON["plugins"]
        assert len(plugins) >= 1
        assert plugins[0]["name"] == "svp"
        assert plugins[0]["source"] == "./svp"
        assert plugins[0]["version"] == "2.1.0"


class TestPluginJsonContent:
    def test_nonempty(self):
        assert isinstance(PLUGIN_JSON_CONTENT, str)
        assert len(PLUGIN_JSON_CONTENT) > 0

    def test_valid_json(self):
        data = json.loads(PLUGIN_JSON_CONTENT)
        assert isinstance(data, dict)

    def test_version_2_1(self):
        data = json.loads(PLUGIN_JSON_CONTENT)
        assert data["version"] == "2.1.0"


class TestMarketplaceJsonContent:
    def test_nonempty(self):
        assert isinstance(MARKETPLACE_JSON_CONTENT, str)
        assert len(MARKETPLACE_JSON_CONTENT) > 0

    def test_valid_json(self):
        data = json.loads(MARKETPLACE_JSON_CONTENT)
        assert isinstance(data, dict)


class TestValidatePluginStructure:
    def test_callable(self):
        assert callable(validate_plugin_structure)

    def test_returns_list(self, tmp_path):
        result = validate_plugin_structure(tmp_path)
        assert isinstance(result, list)

    def test_errors_on_empty_dir(self, tmp_path):
        result = validate_plugin_structure(tmp_path)
        assert len(result) > 0

    def test_valid_structure(self, tmp_path):
        # Create minimal valid structure
        svp = tmp_path / "svp"
        svp.mkdir()
        (svp / ".claude-plugin").mkdir()
        pj = svp / ".claude-plugin" / "plugin.json"
        pj.write_text(json.dumps(PLUGIN_JSON))

        for d in [
            "agents",
            "commands",
            "skills",
            "hooks",
            "scripts",
        ]:
            (svp / d).mkdir()

        skills_orch = svp / "skills" / "orchestration"
        skills_orch.mkdir(parents=True)
        (skills_orch / "SKILL.md").write_text("x")

        td = svp / "scripts" / "toolchain_defaults"
        td.mkdir(parents=True)
        (td / "python_conda_pytest.json").write_text("{}")
        (td / "ruff.toml").write_text("")

        root_cp = tmp_path / ".claude-plugin"
        root_cp.mkdir()
        mp = root_cp / "marketplace.json"
        mp.write_text(json.dumps(MARKETPLACE_JSON))

        result = validate_plugin_structure(tmp_path)
        assert result == []


class TestRunComplianceScan:
    def test_callable(self):
        assert callable(run_compliance_scan)

    def test_returns_list(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        profile = {"delivery": {"environment_recommendation": "conda"}}
        result = run_compliance_scan(tmp_path, src_dir, tests_dir, profile)
        assert isinstance(result, list)


class TestGetBannedPatterns:
    def test_callable(self):
        assert callable(_get_banned_patterns)

    def test_returns_list(self):
        result = _get_banned_patterns("conda")
        assert isinstance(result, list)


class TestScanFileAst:
    def test_callable(self):
        assert callable(_scan_file_ast)

    def test_clean_file(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n")
        result = _scan_file_ast(f, [])
        assert isinstance(result, list)
        assert result == []


class TestComplianceScanMain:
    def test_callable(self):
        assert callable(compliance_scan_main)
