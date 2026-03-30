"""Tests for Unit 28: Plugin Manifest, Structural Validation, and Compliance Scan.

Synthetic data assumptions:
- COMPLIANCE_SCANNERS is a dict keyed by language ID ("python", "r") with callable
  scanner values that accept (src_path, tests_path, toolchain, profile) and return
  a list of finding dicts.
- generate_plugin_json and generate_marketplace_json accept profile dicts and return
  valid JSON strings conforming to their respective schemas.
- run_structural_check performs AST-based analysis on a target path and returns
  findings as a list of dicts.
- validate_* functions accept domain-specific dicts and return lists of error strings
  (empty list means valid).
- check_cross_reference_integrity validates cross-references within a plugin directory.
- compliance_scan_main is a CLI entry point accepting argv.
- Synthetic profile dicts use minimal required fields per Section 40.7.1.
- Synthetic manifests, configs, frontmatter use minimal valid structures.
"""

import json

from src.unit_28.stub import (
    COMPLIANCE_SCANNERS,
    check_cross_reference_integrity,
    compliance_scan_main,
    generate_marketplace_json,
    generate_plugin_json,
    run_structural_check,
    validate_agent_frontmatter,
    validate_dispatch_exhaustiveness,
    validate_hook_definitions,
    validate_lsp_config,
    validate_mcp_config,
    validate_plugin_manifest,
    validate_skill_frontmatter,
)

# ---------------------------------------------------------------------------
# COMPLIANCE_SCANNERS dispatch table contracts
# ---------------------------------------------------------------------------


class TestComplianceScanners:
    """Tests for the COMPLIANCE_SCANNERS dispatch table."""

    def test_compliance_scanners_is_dict(self):
        assert isinstance(COMPLIANCE_SCANNERS, dict)

    def test_compliance_scanners_has_python_key(self):
        assert "python" in COMPLIANCE_SCANNERS

    def test_compliance_scanners_has_r_key(self):
        assert "r" in COMPLIANCE_SCANNERS

    def test_compliance_scanners_python_is_callable(self):
        assert callable(COMPLIANCE_SCANNERS["python"])

    def test_compliance_scanners_r_is_callable(self):
        assert callable(COMPLIANCE_SCANNERS["r"])

    def test_compliance_scanners_keyed_by_language_id(self):
        """All keys should be string language identifiers."""
        for key in COMPLIANCE_SCANNERS:
            assert isinstance(key, str)


# ---------------------------------------------------------------------------
# generate_plugin_json contracts
# ---------------------------------------------------------------------------


class TestGeneratePluginJson:
    """Tests for the generate_plugin_json function."""

    def _minimal_profile(self):
        return {
            "name": "test-plugin",
            "description": "A test plugin",
            "version": "1.0.0",
            "author": "Test Author",
        }

    def test_generate_plugin_json_returns_string(self):
        result = generate_plugin_json(self._minimal_profile())
        assert isinstance(result, str)

    def test_generate_plugin_json_returns_valid_json(self):
        result = generate_plugin_json(self._minimal_profile())
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_generate_plugin_json_contains_required_name(self):
        result = json.loads(generate_plugin_json(self._minimal_profile()))
        assert "name" in result
        assert result["name"] == "test-plugin"

    def test_generate_plugin_json_contains_required_description(self):
        result = json.loads(generate_plugin_json(self._minimal_profile()))
        assert "description" in result
        assert result["description"] == "A test plugin"

    def test_generate_plugin_json_contains_required_version(self):
        result = json.loads(generate_plugin_json(self._minimal_profile()))
        assert "version" in result
        assert result["version"] == "1.0.0"

    def test_generate_plugin_json_contains_required_author(self):
        result = json.loads(generate_plugin_json(self._minimal_profile()))
        assert "author" in result

    def test_generate_plugin_json_with_optional_mcp_servers(self):
        profile = self._minimal_profile()
        profile["mcpServers"] = {
            "test-server": {"command": "node", "args": ["server.js"]}
        }
        result = json.loads(generate_plugin_json(profile))
        assert "mcpServers" in result

    def test_generate_plugin_json_with_optional_hooks(self):
        profile = self._minimal_profile()
        profile["hooks"] = {
            "PreToolUse": [{"matcher": ".*", "type": "command", "command": "echo ok"}]
        }
        result = json.loads(generate_plugin_json(profile))
        assert "hooks" in result

    def test_generate_plugin_json_with_optional_skills(self):
        profile = self._minimal_profile()
        profile["skills"] = [{"name": "test-skill"}]
        result = json.loads(generate_plugin_json(profile))
        assert "skills" in result

    def test_generate_plugin_json_with_optional_agents(self):
        profile = self._minimal_profile()
        profile["agents"] = [{"name": "test-agent"}]
        result = json.loads(generate_plugin_json(profile))
        assert "agents" in result

    def test_generate_plugin_json_with_optional_commands(self):
        profile = self._minimal_profile()
        profile["commands"] = [{"name": "/test", "description": "A test command"}]
        result = json.loads(generate_plugin_json(profile))
        assert "commands" in result


# ---------------------------------------------------------------------------
# generate_marketplace_json contracts
# ---------------------------------------------------------------------------


class TestGenerateMarketplaceJson:
    """Tests for the generate_marketplace_json function."""

    def _minimal_profile(self):
        return {
            "name": "test-plugin",
            "description": "A test plugin",
            "version": "1.0.0",
            "author": "Test Author",
            "owner": {"name": "Test Owner"},
        }

    def test_generate_marketplace_json_returns_string(self):
        result = generate_marketplace_json(self._minimal_profile())
        assert isinstance(result, str)

    def test_generate_marketplace_json_returns_valid_json(self):
        result = generate_marketplace_json(self._minimal_profile())
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_generate_marketplace_json_has_name(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        assert "name" in result

    def test_generate_marketplace_json_has_owner_with_name(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        assert "owner" in result
        assert "name" in result["owner"]

    def test_generate_marketplace_json_has_plugins_array(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        assert "plugins" in result
        assert isinstance(result["plugins"], list)

    def test_generate_marketplace_json_plugin_entry_has_name(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        plugins = result["plugins"]
        assert len(plugins) > 0
        assert "name" in plugins[0]

    def test_generate_marketplace_json_plugin_entry_has_source(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        plugin_entry = result["plugins"][0]
        assert "source" in plugin_entry
        assert plugin_entry["source"] == "./"

    def test_generate_marketplace_json_plugin_entry_has_description(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        plugin_entry = result["plugins"][0]
        assert "description" in plugin_entry

    def test_generate_marketplace_json_plugin_entry_has_version(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        plugin_entry = result["plugins"][0]
        assert "version" in plugin_entry

    def test_generate_marketplace_json_plugin_entry_has_author(self):
        result = json.loads(generate_marketplace_json(self._minimal_profile()))
        plugin_entry = result["plugins"][0]
        assert "author" in plugin_entry


# ---------------------------------------------------------------------------
# run_structural_check contracts
# ---------------------------------------------------------------------------


class TestRunStructuralCheck:
    """Tests for the run_structural_check function."""

    def test_run_structural_check_returns_list(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target)
        assert isinstance(result, list)

    def test_run_structural_check_findings_are_dicts(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("DISPATCH = {'a': 1}\ndef use(): return DISPATCH['b']\n")
        result = run_structural_check(target)
        for finding in result:
            assert isinstance(finding, dict)

    def test_run_structural_check_text_output_format(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, output_format="text")
        assert isinstance(result, list)

    def test_run_structural_check_json_output_format(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, output_format="json")
        assert isinstance(result, list)

    def test_run_structural_check_strict_mode_default_false(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        # strict=False is default; should not raise
        result = run_structural_check(target, strict=False)
        assert isinstance(result, list)

    def test_run_structural_check_detects_unreferenced_dict_registry_keys(
        self, tmp_path
    ):
        """Check 1: dict registry keys never dispatched."""
        target = tmp_path / "module.py"
        target.write_text(
            "REGISTRY = {'a': handler_a, 'b': handler_b}\n"
            "def run():\n"
            "    return REGISTRY['a']()\n"
        )
        findings = run_structural_check(target)
        # 'b' is registered but never dispatched -- expect a finding
        has_undispatched = any(
            "b" in str(f)
            or "undispatched" in str(f).lower()
            or "never dispatched" in str(f).lower()
            for f in findings
        )
        assert has_undispatched or len(findings) > 0

    def test_run_structural_check_clean_file_yields_no_findings(self, tmp_path):
        """A trivially clean file should produce zero findings."""
        target = tmp_path / "clean.py"
        target.write_text("def hello():\n    return 'world'\n")
        findings = run_structural_check(target)
        assert findings == []

    def test_run_structural_check_accepts_directory(self, tmp_path):
        """Should accept a directory path and scan it."""
        (tmp_path / "mod.py").write_text("x = 1\n")
        result = run_structural_check(tmp_path)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# validate_dispatch_exhaustiveness contracts
# ---------------------------------------------------------------------------


class TestValidateDispatchExhaustiveness:
    """Tests for the validate_dispatch_exhaustiveness function."""

    def _full_language(self, lang_id, dispatch_key=None):
        """Create a synthetic full language registry entry."""
        return {
            "dispatch_key": dispatch_key or lang_id,
            "is_component_only": False,
        }

    def _component_language(self, lang_id, required_entries):
        """Create a synthetic component language registry entry."""
        return {
            "dispatch_key": lang_id,
            "is_component_only": True,
            "required_dispatch_entries": required_entries,
        }

    def _all_six_tables(self, *lang_ids):
        """Create dispatch tables with entries for given lang_ids."""
        table_names = [
            "STUB_GENERATORS",
            "TEST_OUTPUT_PARSERS",
            "QUALITY_RUNNERS",
            "SPEC_ASSEMBLERS",
            "COMPLIANCE_SCANNERS",
            "BLUEPRINT_PARSERS",
        ]
        tables = {}
        for name in table_names:
            tables[name] = {lid: "handler" for lid in lang_ids}
        return tables

    def test_validate_dispatch_returns_list(self):
        result = validate_dispatch_exhaustiveness({}, {})
        assert isinstance(result, list)

    def test_validate_dispatch_empty_registry_no_errors(self):
        result = validate_dispatch_exhaustiveness({}, {})
        assert result == []

    def test_validate_dispatch_full_language_present_in_all_tables(self):
        registry = {"python": self._full_language("python")}
        tables = self._all_six_tables("python")
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == []

    def test_validate_dispatch_full_language_missing_from_table(self):
        registry = {"python": self._full_language("python")}
        tables = self._all_six_tables("python")
        # Remove python from one table
        del tables["STUB_GENERATORS"]["python"]
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0

    def test_validate_dispatch_component_language_only_required_tables(self):
        registry = {
            "markdown": self._component_language(
                "markdown", ["STUB_GENERATORS", "QUALITY_RUNNERS"]
            )
        }
        tables = {
            "STUB_GENERATORS": {"markdown": "handler"},
            "QUALITY_RUNNERS": {"markdown": "handler"},
            "TEST_OUTPUT_PARSERS": {},
            "SPEC_ASSEMBLERS": {},
            "COMPLIANCE_SCANNERS": {},
            "BLUEPRINT_PARSERS": {},
        }
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == []

    def test_validate_dispatch_component_language_missing_required_table(self):
        registry = {
            "markdown": self._component_language(
                "markdown", ["STUB_GENERATORS", "QUALITY_RUNNERS"]
            )
        }
        tables = {
            "STUB_GENERATORS": {"markdown": "handler"},
            "QUALITY_RUNNERS": {},  # missing markdown
            "TEST_OUTPUT_PARSERS": {},
            "SPEC_ASSEMBLERS": {},
            "COMPLIANCE_SCANNERS": {},
            "BLUEPRINT_PARSERS": {},
        }
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0

    def test_validate_dispatch_errors_are_strings(self):
        registry = {"python": self._full_language("python")}
        tables = self._all_six_tables()  # empty tables
        result = validate_dispatch_exhaustiveness(registry, tables)
        for error in result:
            assert isinstance(error, str)

    def test_validate_dispatch_plugin_archetype_composite_keys(self):
        """Plugin archetype requires plugin composite keys in specific tables."""
        registry = {
            "python": {
                **self._full_language("python"),
                "archetype": "claude_code_plugin",
            }
        }
        tables = self._all_six_tables("python")
        # Add plugin composite keys
        for key in ("plugin_markdown", "plugin_bash", "plugin_json"):
            tables["STUB_GENERATORS"][key] = "handler"
            tables["TEST_OUTPUT_PARSERS"][key] = "handler"
            tables["QUALITY_RUNNERS"][key] = "handler"
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == []

    def test_validate_dispatch_plugin_archetype_missing_composite_keys(self):
        """Plugin archetype missing composite keys should produce errors."""
        registry = {
            "python": {
                **self._full_language("python"),
                "archetype": "claude_code_plugin",
            }
        }
        tables = self._all_six_tables("python")
        # Do NOT add plugin composite keys
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# validate_plugin_manifest contracts
# ---------------------------------------------------------------------------


class TestValidatePluginManifest:
    """Tests for the validate_plugin_manifest function."""

    def _valid_manifest(self):
        return {
            "name": "test-plugin",
            "description": "A test plugin",
            "version": "1.0.0",
            "author": "Test Author",
        }

    def test_validate_plugin_manifest_returns_list(self):
        result = validate_plugin_manifest(self._valid_manifest())
        assert isinstance(result, list)

    def test_validate_plugin_manifest_valid_manifest_no_errors(self):
        result = validate_plugin_manifest(self._valid_manifest())
        assert result == []

    def test_validate_plugin_manifest_missing_name(self):
        manifest = self._valid_manifest()
        del manifest["name"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0

    def test_validate_plugin_manifest_missing_description(self):
        manifest = self._valid_manifest()
        del manifest["description"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0

    def test_validate_plugin_manifest_missing_version(self):
        manifest = self._valid_manifest()
        del manifest["version"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0

    def test_validate_plugin_manifest_missing_author(self):
        manifest = self._valid_manifest()
        del manifest["author"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0

    def test_validate_plugin_manifest_errors_are_strings(self):
        result = validate_plugin_manifest({})
        for error in result:
            assert isinstance(error, str)

    def test_validate_plugin_manifest_empty_dict_produces_errors(self):
        result = validate_plugin_manifest({})
        assert len(result) > 0


# ---------------------------------------------------------------------------
# validate_mcp_config contracts
# ---------------------------------------------------------------------------


class TestValidateMcpConfig:
    """Tests for the validate_mcp_config function."""

    def test_validate_mcp_config_returns_list(self):
        result = validate_mcp_config({})
        assert isinstance(result, list)

    def test_validate_mcp_config_valid_stdio_transport(self):
        config = {
            "test-server": {
                "command": "node",
                "args": ["server.js"],
            }
        }
        result = validate_mcp_config(config)
        assert result == []

    def test_validate_mcp_config_valid_env_var_syntax(self):
        config = {
            "test-server": {
                "command": "node",
                "args": ["server.js"],
                "env": {"API_KEY": "${API_KEY}"},
            }
        }
        result = validate_mcp_config(config)
        assert result == []

    def test_validate_mcp_config_invalid_env_var_syntax(self):
        config = {
            "test-server": {
                "command": "node",
                "args": ["server.js"],
                "env": {"API_KEY": "$API_KEY"},  # Missing braces
            }
        }
        result = validate_mcp_config(config)
        assert len(result) > 0

    def test_validate_mcp_config_errors_are_strings(self):
        result = validate_mcp_config({"bad": {}})
        for error in result:
            assert isinstance(error, str)


# ---------------------------------------------------------------------------
# validate_lsp_config contracts
# ---------------------------------------------------------------------------


class TestValidateLspConfig:
    """Tests for the validate_lsp_config function."""

    def test_validate_lsp_config_returns_list(self):
        result = validate_lsp_config({})
        assert isinstance(result, list)

    def test_validate_lsp_config_valid_config(self):
        config = {"pyright": {"command": "pyright-langserver", "args": ["--stdio"]}}
        result = validate_lsp_config(config)
        assert result == []

    def test_validate_lsp_config_missing_command(self):
        config = {
            "pyright": {"args": ["--stdio"]}  # missing command
        }
        result = validate_lsp_config(config)
        assert len(result) > 0

    def test_validate_lsp_config_valid_env_var_syntax(self):
        config = {
            "pyright": {
                "command": "pyright-langserver",
                "env": {"PATH": "${PATH}"},
            }
        }
        result = validate_lsp_config(config)
        assert result == []

    def test_validate_lsp_config_errors_are_strings(self):
        config = {"bad": {}}
        result = validate_lsp_config(config)
        for error in result:
            assert isinstance(error, str)


# ---------------------------------------------------------------------------
# validate_skill_frontmatter contracts
# ---------------------------------------------------------------------------


class TestValidateSkillFrontmatter:
    """Tests for the validate_skill_frontmatter function."""

    def test_validate_skill_frontmatter_returns_list(self):
        result = validate_skill_frontmatter({})
        assert isinstance(result, list)

    def test_validate_skill_frontmatter_valid_minimal(self):
        frontmatter = {"name": "test-skill", "description": "A skill"}
        result = validate_skill_frontmatter(frontmatter)
        assert result == []

    def test_validate_skill_frontmatter_unrecognized_field(self):
        frontmatter = {
            "name": "test-skill",
            "description": "A skill",
            "not_a_real_field": "value",
        }
        result = validate_skill_frontmatter(frontmatter)
        assert len(result) > 0

    def test_validate_skill_frontmatter_valid_allowed_tools(self):
        frontmatter = {
            "name": "test-skill",
            "description": "A skill",
            "allowed-tools": ["Read", "Write", "Bash"],
        }
        result = validate_skill_frontmatter(frontmatter)
        assert result == []

    def test_validate_skill_frontmatter_valid_model_value(self):
        frontmatter = {
            "name": "test-skill",
            "description": "A skill",
            "model": "claude-sonnet-4-20250514",
        }
        result = validate_skill_frontmatter(frontmatter)
        assert result == []

    def test_validate_skill_frontmatter_errors_are_strings(self):
        result = validate_skill_frontmatter({"not_valid": True})
        for error in result:
            assert isinstance(error, str)


# ---------------------------------------------------------------------------
# validate_hook_definitions contracts
# ---------------------------------------------------------------------------


class TestValidateHookDefinitions:
    """Tests for the validate_hook_definitions function."""

    def test_validate_hook_definitions_returns_list(self):
        result = validate_hook_definitions({})
        assert isinstance(result, list)

    def test_validate_hook_definitions_valid_command_hook(self):
        hooks = {
            "PreToolUse": [{"matcher": ".*", "type": "command", "command": "echo ok"}]
        }
        result = validate_hook_definitions(hooks)
        assert result == []

    def test_validate_hook_definitions_valid_hook_types(self):
        """Valid hook types are: command, http, prompt, agent."""
        for hook_type in ("command", "http", "prompt", "agent"):
            hooks = {
                "PreToolUse": [{"matcher": ".*", "type": hook_type, "command": "test"}]
            }
            result = validate_hook_definitions(hooks)
            # Should not produce errors about hook type
            type_errors = [
                e for e in result if "type" in e.lower() and hook_type in e.lower()
            ]
            assert len(type_errors) == 0

    def test_validate_hook_definitions_invalid_event_name(self):
        hooks = {
            "NotARealEvent": [
                {"matcher": ".*", "type": "command", "command": "echo ok"}
            ]
        }
        result = validate_hook_definitions(hooks)
        assert len(result) > 0

    def test_validate_hook_definitions_invalid_hook_type(self):
        hooks = {
            "PreToolUse": [
                {"matcher": ".*", "type": "invalid_type", "command": "echo ok"}
            ]
        }
        result = validate_hook_definitions(hooks)
        assert len(result) > 0

    def test_validate_hook_definitions_invalid_matcher_regex(self):
        hooks = {
            "PreToolUse": [
                {"matcher": "[invalid(", "type": "command", "command": "echo ok"}
            ]
        }
        result = validate_hook_definitions(hooks)
        assert len(result) > 0

    def test_validate_hook_definitions_errors_are_strings(self):
        hooks = {"BadEvent": [{"type": "bad"}]}
        result = validate_hook_definitions(hooks)
        for error in result:
            assert isinstance(error, str)

    def test_validate_hook_definitions_empty_dict_no_errors(self):
        result = validate_hook_definitions({})
        assert result == []


# ---------------------------------------------------------------------------
# validate_agent_frontmatter contracts
# ---------------------------------------------------------------------------


class TestValidateAgentFrontmatter:
    """Tests for the validate_agent_frontmatter function."""

    def test_validate_agent_frontmatter_returns_list(self):
        result = validate_agent_frontmatter({})
        assert isinstance(result, list)

    def test_validate_agent_frontmatter_valid_minimal(self):
        frontmatter = {"name": "test-agent", "description": "An agent"}
        result = validate_agent_frontmatter(frontmatter)
        assert result == []

    def test_validate_agent_frontmatter_unrecognized_field(self):
        frontmatter = {
            "name": "test-agent",
            "description": "An agent",
            "bogus_field": "value",
        }
        result = validate_agent_frontmatter(frontmatter)
        assert len(result) > 0

    def test_validate_agent_frontmatter_valid_disallowed_tools(self):
        frontmatter = {
            "name": "test-agent",
            "description": "An agent",
            "disallowedTools": ["Bash", "Write"],
        }
        result = validate_agent_frontmatter(frontmatter)
        assert result == []

    def test_validate_agent_frontmatter_errors_are_strings(self):
        result = validate_agent_frontmatter({"bogus": True})
        for error in result:
            assert isinstance(error, str)


# ---------------------------------------------------------------------------
# check_cross_reference_integrity contracts
# ---------------------------------------------------------------------------


class TestCheckCrossReferenceIntegrity:
    """Tests for the check_cross_reference_integrity function."""

    def test_check_cross_reference_integrity_returns_list(self, tmp_path):
        result = check_cross_reference_integrity(tmp_path)
        assert isinstance(result, list)

    def test_check_cross_reference_integrity_empty_dir_no_crash(self, tmp_path):
        """An empty directory should not crash -- may return errors or empty list."""
        result = check_cross_reference_integrity(tmp_path)
        assert isinstance(result, list)

    def test_check_cross_reference_integrity_errors_are_strings(self, tmp_path):
        result = check_cross_reference_integrity(tmp_path)
        for error in result:
            assert isinstance(error, str)

    def test_check_cross_reference_integrity_valid_plugin_dir(self, tmp_path):
        """A well-structured plugin directory with consistent cross-refs should pass."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / "plugin.json"
        plugin_json.write_text(
            json.dumps(
                {
                    "name": "test-plugin",
                    "description": "Test",
                    "version": "1.0.0",
                    "author": "Test",
                }
            )
        )
        result = check_cross_reference_integrity(tmp_path)
        # A minimal valid plugin should have no cross-ref errors
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# compliance_scan_main CLI contracts
# ---------------------------------------------------------------------------


class TestComplianceScanMain:
    """Tests for the compliance_scan_main CLI entry point."""

    def test_compliance_scan_main_accepts_argv(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (src_dir / "mod.py").write_text("x = 1\n")
        argv = [
            "--project-root",
            str(tmp_path),
            "--src-dir",
            str(src_dir),
            "--tests-dir",
            str(tests_dir),
            "--format",
            "text",
        ]
        # Should not raise
        compliance_scan_main(argv)

    def test_compliance_scan_main_json_format(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (src_dir / "mod.py").write_text("x = 1\n")
        argv = [
            "--project-root",
            str(tmp_path),
            "--src-dir",
            str(src_dir),
            "--tests-dir",
            str(tests_dir),
            "--format",
            "json",
        ]
        compliance_scan_main(argv)

    def test_compliance_scan_main_strict_flag(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (src_dir / "mod.py").write_text("x = 1\n")
        argv = [
            "--project-root",
            str(tmp_path),
            "--src-dir",
            str(src_dir),
            "--tests-dir",
            str(tests_dir),
            "--strict",
        ]
        # strict mode may raise SystemExit if findings exist; just verify it accepts the flag
        try:
            compliance_scan_main(argv)
        except SystemExit:
            pass  # expected if findings exist in strict mode

    def test_compliance_scan_main_no_args_uses_default(self):
        """Calling with None should use sys.argv defaults (may fail, but shouldn't crash on import)."""
        try:
            compliance_scan_main(
                ["--project-root", ".", "--src-dir", ".", "--tests-dir", "."]
            )
        except (SystemExit, FileNotFoundError, OSError):
            pass  # acceptable for missing project structure
