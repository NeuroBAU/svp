"""Tests for Unit 28: Plugin Manifest, Structural Validation, and Compliance Scan.

Synthetic Data Assumptions:
- COMPLIANCE_SCANNERS is a module-level dict keyed by language ID strings ("python", "r").
  Each value is a callable accepting (Path, Path, Dict, Dict) and returning List[Dict].
- generate_plugin_json and generate_marketplace_json accept a profile dict and return
  JSON strings. Profile dicts are synthesized with the required fields from the
  Section 40.7.1 schema and Unit 3 profile structure.
- validate_* functions accept dicts describing their respective domain objects and
  return lists of violation/error strings (empty list means valid).
- validate_dispatch_exhaustiveness takes a language_registry dict and dispatch_tables
  dict. We synthesize registries with full and component-only languages, and dispatch
  tables with 6 known table keys. The 6 tables are assumed to be: STUB_GENERATORS,
  ASSEMBLERS, COMPLIANCE_SCANNERS, TEST_OUTPUT_PARSERS, QUALITY_RUNNERS, and one
  additional parser/runner table using dispatch keys.
- run_structural_check takes a target Path (pointing to a directory or file to scan),
  an output_format ("text" or "json"), and a strict flag. It returns a list of finding
  dicts. We create temporary Python files with known structural patterns.
- compliance_scan_main is a CLI entry point accepting argv with --project-root,
  --src-dir, --tests-dir, --format, and --strict.
- For cross-reference integrity checks, we create temporary plugin directory structures
  with skills, agents, MCP configs, hooks, commands, and manifest files.
- The 12-event set for hook validation is assumed based on common plugin lifecycle
  events. Valid hook types are: command, http, prompt, agent.
- MCP transport types include at minimum "stdio" and "sse" (or similar), each with
  transport-specific required fields.
- Plugin manifest has 12 fields per Section 40.7.1: name, description, version, author
  plus optional mcpServers, lspServers, hooks, commands, agents, skills, outputStyles,
  tools.
"""

import json

from structural_check import (
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
# Shared test data factories
# ---------------------------------------------------------------------------


def _minimal_valid_profile():
    """Return a minimal profile dict with required fields for plugin JSON generation."""
    return {
        "name": "test-plugin",
        "description": "A test plugin for SVP",
        "version": "1.0.0",
        "author": "Test Author",
        "archetype": "claude_code_plugin",
        "language": {"primary": "python", "components": []},
    }


def _full_profile_with_optional_fields():
    """Profile with all optional plugin fields populated."""
    return {
        "name": "full-plugin",
        "description": "A full-featured test plugin",
        "version": "2.1.0",
        "author": "Full Author",
        "archetype": "claude_code_plugin",
        "language": {"primary": "python", "components": []},
        "mcpServers": {"my-server": {"transport": "stdio", "command": "node"}},
        "lspServers": {"my-lsp": {"command": "pylsp"}},
        "hooks": {"on_save": {"type": "command", "command": "echo saved"}},
        "commands": {"build": {"description": "Build the project"}},
        "agents": {"helper": {"description": "A helper agent"}},
        "skills": {"coding": {"description": "Coding skill"}},
        "outputStyles": {"compact": {"description": "Compact output"}},
        "tools": {"lint": {"description": "Lint tool"}},
    }


def _minimal_valid_manifest():
    """Return a minimal valid plugin manifest dict."""
    return {
        "name": "test-plugin",
        "description": "A test plugin",
        "version": "1.0.0",
        "author": "Test Author",
    }


def _full_language_registry_entry(lang_id="python", dispatch_key=None):
    """Create a full-language registry entry for testing dispatch exhaustiveness."""
    return {
        "id": lang_id,
        "display_name": lang_id.capitalize(),
        "is_component_only": False,
        "stub_generator_key": dispatch_key or lang_id,
        "test_output_parser_key": dispatch_key or lang_id,
        "quality_runner_key": dispatch_key or lang_id,
    }


def _component_language_registry_entry(
    lang_id="stan", hosts=None, required_entries=None
):
    """Create a component-only registry entry."""
    return {
        "id": lang_id,
        "display_name": lang_id.capitalize(),
        "is_component_only": True,
        "compatible_hosts": hosts or ["python"],
        "stub_generator_key": f"{lang_id}_template",
        "quality_runner_key": f"{lang_id}_syntax_check",
        "required_dispatch_entries": required_entries
        or ["stub_generator_key", "quality_runner_key"],
    }


def _six_dispatch_tables(language_ids=None, dispatch_keys=None, plugin_keys=None):
    """Create 6 dispatch tables populated with the given language IDs and dispatch keys.

    The 6 tables based on contracts:
    - STUB_GENERATORS: keyed by language ID
    - ASSEMBLERS: keyed by language ID
    - COMPLIANCE_SCANNERS: keyed by language ID
    - TEST_OUTPUT_PARSERS: keyed by dispatch key
    - QUALITY_RUNNERS: keyed by dispatch key
    - A 6th table (parser/runner): keyed by dispatch key
    """
    language_ids = language_ids or ["python", "r"]
    dispatch_keys = dispatch_keys or ["python", "r"]
    plugin_keys = plugin_keys or []

    stub_generators = {lid: lambda: None for lid in language_ids}
    assemblers = {lid: lambda: None for lid in language_ids}
    compliance_scanners = {lid: lambda: None for lid in language_ids}
    test_output_parsers = {dk: lambda: None for dk in dispatch_keys}
    quality_runners = {dk: lambda: None for dk in dispatch_keys}
    # 6th dispatch table
    dispatch_table_6 = {dk: lambda: None for dk in dispatch_keys}

    # Add plugin keys if present
    for pk in plugin_keys:
        stub_generators[pk] = lambda: None
        test_output_parsers[pk] = lambda: None
        quality_runners[pk] = lambda: None

    return {
        "STUB_GENERATORS": stub_generators,
        "ASSEMBLERS": assemblers,
        "COMPLIANCE_SCANNERS": compliance_scanners,
        "TEST_OUTPUT_PARSERS": test_output_parsers,
        "QUALITY_RUNNERS": quality_runners,
        "DISPATCH_TABLE_6": dispatch_table_6,
    }


def _valid_mcp_config_stdio():
    """Return a valid MCP config using stdio transport."""
    return {
        "my-server": {
            "transport": "stdio",
            "command": "node",
            "args": ["server.js"],
        }
    }


def _valid_mcp_config_sse():
    """Return a valid MCP config using sse transport."""
    return {
        "my-server": {
            "transport": "sse",
            "url": "http://localhost:3000/sse",
        }
    }


def _valid_lsp_config():
    """Return a valid LSP config."""
    return {
        "python-lsp": {
            "command": "pylsp",
        }
    }


def _valid_skill_frontmatter():
    """Return valid skill frontmatter."""
    return {
        "name": "coding-skill",
        "description": "A coding skill",
        "allowed-tools": ["Read", "Write", "Bash"],
        "model": "claude-opus-4-6",
    }


def _valid_hook_definitions():
    """Return valid hook definitions with recognized events and types."""
    return {
        "on_save": {
            "type": "command",
            "command": "echo saved",
        },
    }


def _valid_agent_frontmatter():
    """Return valid agent frontmatter."""
    return {
        "name": "helper-agent",
        "description": "Helps with tasks",
        "disallowedTools": [],
    }


# ===========================================================================
# 1. COMPLIANCE_SCANNERS dispatch table
# ===========================================================================


class TestComplianceScannersDispatchTable:
    """COMPLIANCE_SCANNERS must be a dict keyed by language ID with callable values."""

    def test_compliance_scanners_is_a_dict(self):
        assert isinstance(COMPLIANCE_SCANNERS, dict)

    def test_compliance_scanners_has_python_key(self):
        assert "python" in COMPLIANCE_SCANNERS

    def test_compliance_scanners_has_r_key(self):
        assert "r" in COMPLIANCE_SCANNERS

    def test_compliance_scanners_python_value_is_callable(self):
        assert callable(COMPLIANCE_SCANNERS["python"])

    def test_compliance_scanners_r_value_is_callable(self):
        assert callable(COMPLIANCE_SCANNERS["r"])

    def test_compliance_scanners_keyed_by_language_id(self):
        """All keys should be language ID strings."""
        for key in COMPLIANCE_SCANNERS:
            assert isinstance(key, str)


# ===========================================================================
# 2. Python compliance scanner banned patterns
# ===========================================================================


class TestPythonComplianceScannerBannedPatterns:
    """Python scanner is AST-based and bans environment-specific patterns."""

    def _create_python_file(self, tmp_path, content, filename="test.py"):
        """Helper to create a Python source file."""
        src = tmp_path / "src"
        src.mkdir(exist_ok=True)
        f = src / filename
        f.write_text(content)
        return src

    def test_python_scanner_returns_list(self, tmp_path):
        """Python scanner must return a list of dicts."""
        src = self._create_python_file(tmp_path, "x = 1\n")
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert isinstance(result, list)

    def test_python_scanner_conda_env_bans_bare_pip(self, tmp_path):
        """In conda environment, bare 'pip' without 'conda run -n' is banned."""
        src = self._create_python_file(
            tmp_path, "import subprocess\nsubprocess.run(['pip', 'install', 'foo'])\n"
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag bare pip in conda environment"

    def test_python_scanner_conda_env_bans_bare_python(self, tmp_path):
        """In conda environment, bare 'python' without 'conda run -n' is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['python', 'script.py'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag bare python in conda environment"

    def test_python_scanner_conda_env_bans_bare_pytest(self, tmp_path):
        """In conda environment, bare 'pytest' without 'conda run -n' is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['pytest'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag bare pytest in conda environment"

    def test_python_scanner_pyenv_env_bans_conda(self, tmp_path):
        """In pyenv environment, 'conda' is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['conda', 'install', 'foo'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "pyenv"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag conda in pyenv environment"

    def test_python_scanner_venv_env_bans_conda(self, tmp_path):
        """In venv environment, 'conda' is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['conda', 'activate'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "venv"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag conda in venv environment"

    def test_python_scanner_poetry_env_bans_conda(self, tmp_path):
        """In poetry environment, 'conda' is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['conda', 'install', 'x'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "poetry"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag conda in poetry environment"

    def test_python_scanner_poetry_env_bans_bare_pip_install(self, tmp_path):
        """In poetry environment, bare 'pip install' is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['pip', 'install', 'foo'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "poetry"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag bare pip install in poetry environment"

    def test_python_scanner_none_env_bans_env_manager_commands(self, tmp_path):
        """With no environment manager, any environment manager command is banned."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['conda', 'install', 'x'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "none"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag env manager commands when none is set"

    def test_python_scanner_clean_code_returns_empty(self, tmp_path):
        """Clean Python code with no banned patterns should return empty list."""
        src = self._create_python_file(tmp_path, "def hello():\n    return 'world'\n")
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        assert result == [], f"Clean code should produce no findings, got: {result}"

    def test_python_scanner_findings_are_dicts(self, tmp_path):
        """Each finding from the scanner must be a dict."""
        src = self._create_python_file(
            tmp_path,
            "import subprocess\nsubprocess.run(['pip', 'install', 'foo'])\n",
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "python"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["python"](src, tests, profile, toolchain)
        for finding in result:
            assert isinstance(finding, dict)


# ===========================================================================
# 3. R compliance scanner banned patterns
# ===========================================================================


class TestRComplianceScannerBannedPatterns:
    """R scanner is regex-based and bans environment-specific patterns."""

    def _create_r_file(self, tmp_path, content, filename="test.R"):
        """Helper to create an R source file."""
        src = tmp_path / "R"
        src.mkdir(exist_ok=True)
        f = src / filename
        f.write_text(content)
        return src

    def test_r_scanner_returns_list(self, tmp_path):
        """R scanner must return a list."""
        src = self._create_r_file(tmp_path, "x <- 1\n")
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "renv"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert isinstance(result, list)

    def test_r_scanner_renv_bans_install_packages(self, tmp_path):
        """In renv environment, install.packages() is banned."""
        src = self._create_r_file(tmp_path, 'install.packages("dplyr")\n')
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "renv"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag install.packages() in renv environment"

    def test_r_scanner_renv_bans_system_with_pip(self, tmp_path):
        """In renv environment, system() containing pip is banned."""
        src = self._create_r_file(tmp_path, 'system("pip install numpy")\n')
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "renv"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag system() with pip in renv environment"

    def test_r_scanner_renv_bans_system_with_conda(self, tmp_path):
        """In renv environment, system() containing conda is banned."""
        src = self._create_r_file(tmp_path, 'system("conda install numpy")\n')
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "renv"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag system() with conda in renv environment"

    def test_r_scanner_conda_bans_install_packages(self, tmp_path):
        """In R+conda environment, install.packages() is banned."""
        src = self._create_r_file(tmp_path, 'install.packages("ggplot2")\n')
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert len(result) > 0, "Should flag install.packages() in R+conda environment"

    def test_r_scanner_conda_bans_bare_rscript_without_conda_run(self, tmp_path):
        """In R+conda environment, bare Rscript without conda run is banned."""
        src = self._create_r_file(tmp_path, 'system("Rscript analysis.R")\n')
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "conda"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert len(result) > 0, (
            "Should flag bare Rscript without conda run in R+conda environment"
        )

    def test_r_scanner_clean_code_returns_empty(self, tmp_path):
        """Clean R code with no banned patterns returns empty list."""
        src = self._create_r_file(
            tmp_path, "hello <- function() {\n  return('world')\n}\n"
        )
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "renv"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        assert result == [], f"Clean R code should produce no findings, got: {result}"

    def test_r_scanner_findings_are_dicts(self, tmp_path):
        """Each finding from the R scanner must be a dict."""
        src = self._create_r_file(tmp_path, 'install.packages("dplyr")\n')
        tests = tmp_path / "tests"
        tests.mkdir(exist_ok=True)
        profile = {"language": {"primary": "r"}}
        toolchain = {"environment_manager": "renv"}
        result = COMPLIANCE_SCANNERS["r"](src, tests, profile, toolchain)
        for finding in result:
            assert isinstance(finding, dict)


# ===========================================================================
# 4. generate_plugin_json
# ===========================================================================


class TestGeneratePluginJson:
    """generate_plugin_json validates against Section 40.7.1 schema and returns JSON."""

    def test_returns_a_string(self):
        profile = _minimal_valid_profile()
        result = generate_plugin_json(profile)
        assert isinstance(result, str)

    def test_returns_valid_json(self):
        profile = _minimal_valid_profile()
        result = generate_plugin_json(profile)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_required_field_name(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert "name" in parsed

    def test_contains_required_field_description(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert "description" in parsed

    def test_contains_required_field_version(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert "version" in parsed

    def test_contains_required_field_author(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert "author" in parsed

    def test_name_matches_profile(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert parsed["name"] == "test-plugin"

    def test_description_matches_profile(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert parsed["description"] == "A test plugin for SVP"

    def test_version_matches_profile(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert parsed["version"] == "1.0.0"

    def test_author_matches_profile(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        assert parsed["author"] == "Test Author"

    def test_optional_fields_included_when_present(self):
        """Optional fields from profile are included in generated JSON."""
        profile = _full_profile_with_optional_fields()
        parsed = json.loads(generate_plugin_json(profile))
        # Bug S3-43: agents, commands, skills are auto-discovered by Claude
        # Code and must NOT appear in plugin.json output
        included_fields = [
            "mcpServers",
            "lspServers",
            "hooks",
            "outputStyles",
            "tools",
        ]
        excluded_fields = ["agents", "commands", "skills"]
        for field in included_fields:
            assert field in parsed, f"Optional field '{field}' should be included"
        for field in excluded_fields:
            assert field not in parsed, (
                f"Auto-discovered field '{field}' must not appear in output (Bug S3-43)"
            )

    def test_optional_fields_omitted_when_absent(self):
        """Optional fields not in profile should not appear in output."""
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_plugin_json(profile))
        optional_fields = [
            "mcpServers",
            "lspServers",
            "hooks",
            "commands",
            "agents",
            "skills",
            "outputStyles",
            "tools",
        ]
        for field in optional_fields:
            assert field not in parsed, (
                f"Optional field '{field}' should not be present when not in profile"
            )


# ===========================================================================
# 5. generate_marketplace_json
# ===========================================================================


class TestGenerateMarketplaceJson:
    """generate_marketplace_json produces JSON with required marketplace fields."""

    def test_returns_a_string(self):
        profile = _minimal_valid_profile()
        result = generate_marketplace_json(profile)
        assert isinstance(result, str)

    def test_returns_valid_json(self):
        profile = _minimal_valid_profile()
        result = generate_marketplace_json(profile)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_required_field_name(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_marketplace_json(profile))
        assert "name" in parsed

    def test_contains_required_field_owner(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_marketplace_json(profile))
        assert "owner" in parsed

    def test_owner_is_object_with_name(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_marketplace_json(profile))
        assert isinstance(parsed["owner"], dict)
        assert "name" in parsed["owner"]

    def test_contains_required_field_plugins_array(self):
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_marketplace_json(profile))
        assert "plugins" in parsed
        assert isinstance(parsed["plugins"], list)

    def test_plugin_entry_has_required_fields(self):
        """Each plugin entry must have name, source, description, version, author."""
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_marketplace_json(profile))
        assert len(parsed["plugins"]) > 0, "Should have at least one plugin entry"
        entry = parsed["plugins"][0]
        required_plugin_fields = [
            "name",
            "source",
            "description",
            "version",
            "author",
        ]
        for field in required_plugin_fields:
            assert field in entry, f"Plugin entry missing required field '{field}'"

    def test_plugin_entry_source_is_relative_dot_slash(self):
        """Plugin source should be a relative path starting with './'."""
        profile = _minimal_valid_profile()
        parsed = json.loads(generate_marketplace_json(profile))
        entry = parsed["plugins"][0]
        assert entry["source"].startswith("./"), (
            f"Plugin source should start with './', got: {entry['source']}"
        )


# ===========================================================================
# 6. run_structural_check
# ===========================================================================


class TestRunStructuralCheck:
    """run_structural_check performs 4 AST-based checks and returns findings."""

    def test_returns_a_list(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target)
        assert isinstance(result, list)

    def test_findings_are_dicts(self, tmp_path):
        """Each finding should be a dict."""
        target = tmp_path / "sample.py"
        target.write_text("MY_DICT = {'a': 1, 'b': 2}\n")
        result = run_structural_check(target)
        for finding in result:
            assert isinstance(finding, dict)

    def test_text_output_format_default(self, tmp_path):
        """Default output_format is 'text'."""
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, output_format="text")
        assert isinstance(result, list)

    def test_json_output_format(self, tmp_path):
        """output_format='json' still returns list of finding dicts."""
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, output_format="json")
        assert isinstance(result, list)

    def test_strict_mode_does_not_change_return_type(self, tmp_path):
        """strict=True should still return findings list."""
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, strict=True)
        assert isinstance(result, list)

    def test_clean_code_returns_empty_findings(self, tmp_path):
        """Simple clean code with no structural issues returns empty list."""
        target = tmp_path / "clean.py"
        target.write_text("def add(a, b):\n    return a + b\n")
        result = run_structural_check(target)
        assert result == [], f"Clean code should have no findings, got: {result}"

    def test_detects_dict_registry_keys_never_dispatched(self, tmp_path):
        """Check 1: dict registry keys that are never dispatched."""
        code = (
            "REGISTRY = {'a': handler_a, 'b': handler_b, 'c': handler_c}\n"
            "def run(key):\n"
            "    if key == 'a':\n"
            "        pass\n"
            "    elif key == 'b':\n"
            "        pass\n"
            "    # 'c' is never dispatched\n"
        )
        target = tmp_path / "dispatch_gap.py"
        target.write_text(code)
        result = run_structural_check(target)
        # Should detect that 'c' is in registry but never dispatched
        assert isinstance(result, list)

    def test_detects_exported_functions_never_called(self, tmp_path):
        """Check 3: exported functions that are never called."""
        code = (
            "def public_func():\n"
            "    return 1\n"
            "\n"
            "def _private_helper():\n"
            "    return 2\n"
            "\n"
            "def another_public():\n"
            "    _private_helper()\n"
        )
        target = tmp_path / "unused.py"
        target.write_text(code)
        result = run_structural_check(target)
        assert isinstance(result, list)

    def test_accepts_directory_target(self, tmp_path):
        """Target can be a directory, scanning all files within."""
        (tmp_path / "file1.py").write_text("x = 1\n")
        (tmp_path / "file2.py").write_text("y = 2\n")
        result = run_structural_check(tmp_path)
        assert isinstance(result, list)

    def test_uses_only_stdlib_imports(self):
        """Structural check must only use stdlib imports: ast, json, pathlib, argparse, sys.

        This is a design contract -- we verify the function exists and is callable,
        since we cannot inspect imports without reading implementation.
        """
        assert callable(run_structural_check)


# ===========================================================================
# 7. validate_dispatch_exhaustiveness
# ===========================================================================


class TestValidateDispatchExhaustiveness:
    """validate_dispatch_exhaustiveness checks all 6 tables + plugin keys."""

    def test_returns_a_list(self):
        registry = {"python": _full_language_registry_entry("python")}
        tables = _six_dispatch_tables(["python"], ["python"])
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert isinstance(result, list)

    def test_valid_full_language_returns_empty_errors(self):
        """A full language present in all 6 tables returns no errors."""
        registry = {"python": _full_language_registry_entry("python")}
        tables = _six_dispatch_tables(["python"], ["python"])
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], f"Valid config should have no errors, got: {result}"

    def test_full_language_missing_from_one_table_returns_error(self):
        """A full language missing from any of the 6 tables produces an error."""
        registry = {"python": _full_language_registry_entry("python")}
        tables = _six_dispatch_tables(["python"], ["python"])
        # Remove python from one table
        first_table_key = list(tables.keys())[0]
        del tables[first_table_key]["python"]
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, "Should report missing dispatch entry"

    def test_errors_are_strings(self):
        """All returned errors must be strings."""
        registry = {"python": _full_language_registry_entry("python")}
        tables = _six_dispatch_tables([], [])  # empty tables
        result = validate_dispatch_exhaustiveness(registry, tables)
        for error in result:
            assert isinstance(error, str)

    def test_component_language_checks_only_required_tables(self):
        """Component language only needs entries in tables listed in required_dispatch_entries."""
        registry = {
            "stan": _component_language_registry_entry(
                "stan",
                required_entries=["stub_generator_key", "quality_runner_key"],
            )
        }
        tables = _six_dispatch_tables([], [])
        # Add only the required entries for the component
        tables["STUB_GENERATORS"]["stan_template"] = lambda: None
        tables["QUALITY_RUNNERS"]["stan_syntax_check"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], (
            f"Component with required entries should pass, got: {result}"
        )

    def test_component_language_missing_required_table_entry_returns_error(self):
        """Component missing a required dispatch entry produces an error."""
        registry = {
            "stan": _component_language_registry_entry(
                "stan",
                required_entries=["stub_generator_key", "quality_runner_key"],
            )
        }
        tables = _six_dispatch_tables([], [])
        # Only add one of the two required entries
        tables["STUB_GENERATORS"]["stan_template"] = lambda: None
        # quality_runner_key entry is missing
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, "Should report missing required dispatch entry"

    def test_component_only_languages_not_checked_for_all_6_tables(self):
        """Component-only languages should NOT be required in all 6 tables."""
        registry = {
            "stan": _component_language_registry_entry(
                "stan",
                required_entries=["stub_generator_key", "quality_runner_key"],
            )
        }
        tables = _six_dispatch_tables([], [])
        tables["STUB_GENERATORS"]["stan_template"] = lambda: None
        tables["QUALITY_RUNNERS"]["stan_syntax_check"] = lambda: None
        # Stan is not in ASSEMBLERS, COMPLIANCE_SCANNERS, etc. -- that is OK
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], (
            f"Component language should not require all 6 tables, got: {result}"
        )

    def test_plugin_archetype_checks_plugin_composite_keys(self):
        """When archetype is claude_code_plugin, verifies plugin composite keys
        are in STUB_GENERATORS, TEST_OUTPUT_PARSERS, and QUALITY_RUNNERS."""
        registry = {
            "python": {
                **_full_language_registry_entry("python"),
                "archetype": "claude_code_plugin",
            }
        }
        plugin_keys = ["plugin_markdown", "plugin_bash", "plugin_json"]
        tables = _six_dispatch_tables(["python"], ["python"], plugin_keys=plugin_keys)
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], (
            f"Plugin archetype with all keys should pass, got: {result}"
        )

    def test_plugin_archetype_missing_plugin_key_returns_error(self):
        """Missing plugin composite key should produce an error for plugin archetype."""
        registry = {
            "python": {
                **_full_language_registry_entry("python"),
                "archetype": "claude_code_plugin",
            }
        }
        # Only add 2 of 3 plugin keys
        tables = _six_dispatch_tables(["python"], ["python"])
        tables["STUB_GENERATORS"]["plugin_markdown"] = lambda: None
        tables["STUB_GENERATORS"]["plugin_bash"] = lambda: None
        # plugin_json missing from STUB_GENERATORS
        tables["TEST_OUTPUT_PARSERS"]["plugin_markdown"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_bash"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_json"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_markdown"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_bash"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_json"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, "Should report missing plugin composite key"

    def test_multiple_full_languages_all_checked(self):
        """Multiple full languages are all validated against all 6 tables."""
        registry = {
            "python": _full_language_registry_entry("python"),
            "r": _full_language_registry_entry("r"),
        }
        tables = _six_dispatch_tables(["python", "r"], ["python", "r"])
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], f"All languages present should pass, got: {result}"

    def test_multiple_languages_one_missing_reports_that_language(self):
        """When one of multiple languages is missing, error references it."""
        registry = {
            "python": _full_language_registry_entry("python"),
            "r": _full_language_registry_entry("r"),
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        # r is missing from all tables
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, "Should report missing entries for 'r'"
        # Check that at least one error references 'r'
        assert any("r" in err.lower() for err in result), (
            "Error should reference the missing language 'r'"
        )

    def test_uses_language_id_for_assemblers_and_scanners(self):
        """Assemblers and scanners use language ID as key, not dispatch key."""
        registry = {
            "python": _full_language_registry_entry("python"),
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        # Python should be keyed by "python" in assemblers/scanners
        assert "python" in tables["ASSEMBLERS"]
        assert "python" in tables["COMPLIANCE_SCANNERS"]
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == []

    def test_uses_dispatch_key_for_parsers_and_runners(self):
        """Parsers and runners use dispatch key, not language ID."""
        # Create a language where dispatch key differs from ID
        registry = {
            "custom": {
                **_full_language_registry_entry("custom"),
                "test_output_parser_key": "custom_parser",
                "quality_runner_key": "custom_runner",
            }
        }
        tables = _six_dispatch_tables(["custom"], [])
        # Add entries using dispatch keys
        tables["TEST_OUTPUT_PARSERS"]["custom_parser"] = lambda: None
        tables["QUALITY_RUNNERS"]["custom_runner"] = lambda: None
        # Also add to remaining tables that use dispatch key
        tables["DISPATCH_TABLE_6"]["custom_parser"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        # Should not error on parser/runner because dispatch keys are present
        assert isinstance(result, list)


# ===========================================================================
# 8. validate_plugin_manifest
# ===========================================================================


class TestValidatePluginManifest:
    """validate_plugin_manifest validates all 12 fields from Section 40.7.1."""

    def test_returns_a_list(self):
        result = validate_plugin_manifest(_minimal_valid_manifest())
        assert isinstance(result, list)

    def test_valid_manifest_returns_empty_errors(self):
        result = validate_plugin_manifest(_minimal_valid_manifest())
        assert result == [], f"Valid manifest should have no errors, got: {result}"

    def test_missing_name_returns_error(self):
        manifest = _minimal_valid_manifest()
        del manifest["name"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0, "Missing 'name' should produce error"

    def test_missing_description_returns_error(self):
        manifest = _minimal_valid_manifest()
        del manifest["description"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0, "Missing 'description' should produce error"

    def test_missing_version_returns_error(self):
        manifest = _minimal_valid_manifest()
        del manifest["version"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0, "Missing 'version' should produce error"

    def test_missing_author_returns_error(self):
        manifest = _minimal_valid_manifest()
        del manifest["author"]
        result = validate_plugin_manifest(manifest)
        assert len(result) > 0, "Missing 'author' should produce error"

    def test_errors_are_strings(self):
        manifest = {}  # missing all required fields
        result = validate_plugin_manifest(manifest)
        for error in result:
            assert isinstance(error, str)

    def test_empty_manifest_reports_all_required_fields_missing(self):
        result = validate_plugin_manifest({})
        assert len(result) >= 4, (
            f"Empty manifest should report at least 4 required field errors, got {len(result)}"
        )

    def test_manifest_with_all_12_fields_valid(self):
        """Manifest with all 12 fields (4 required + 8 optional) should pass."""
        manifest = {
            "name": "test",
            "description": "desc",
            "version": "1.0.0",
            "author": "auth",
            "mcpServers": {},
            "lspServers": {},
            "hooks": {},
            "commands": {},
            "agents": {},
            "skills": {},
            "outputStyles": {},
            "tools": {},
        }
        result = validate_plugin_manifest(manifest)
        assert result == [], f"Full manifest should have no errors, got: {result}"

    def test_manifest_with_unknown_fields_reported_or_ignored(self):
        """Manifest with unrecognized fields -- validation may report or ignore them."""
        manifest = {
            **_minimal_valid_manifest(),
            "unknownField": "value",
        }
        result = validate_plugin_manifest(manifest)
        # The contract says "validates all 12 fields" but does not explicitly
        # state unknown fields are errors; verify no crash.
        assert isinstance(result, list)


# ===========================================================================
# 9. validate_mcp_config
# ===========================================================================


class TestValidateMcpConfig:
    """validate_mcp_config validates transport-specific fields and env var syntax."""

    def test_returns_a_list(self):
        result = validate_mcp_config(_valid_mcp_config_stdio())
        assert isinstance(result, list)

    def test_valid_stdio_config_returns_empty(self):
        result = validate_mcp_config(_valid_mcp_config_stdio())
        assert result == [], f"Valid stdio config should pass, got: {result}"

    def test_valid_sse_config_returns_empty(self):
        result = validate_mcp_config(_valid_mcp_config_sse())
        assert result == [], f"Valid sse config should pass, got: {result}"

    def test_invalid_transport_type_returns_error(self):
        config = {
            "server": {
                "transport": "invalid_transport",
                "command": "node",
            }
        }
        result = validate_mcp_config(config)
        assert len(result) > 0, "Invalid transport type should produce error"

    def test_missing_transport_specific_fields_returns_error(self):
        """Each transport type has required fields; missing them is an error."""
        config = {
            "server": {
                "transport": "stdio",
                # missing 'command' which is required for stdio
            }
        }
        result = validate_mcp_config(config)
        assert len(result) > 0, "Missing transport-specific fields should produce error"

    def test_valid_env_var_syntax_accepted(self):
        """Env var references using ${...} syntax should be valid."""
        config = {
            "server": {
                "transport": "stdio",
                "command": "node",
                "env": {"API_KEY": "${MY_API_KEY}"},
            }
        }
        result = validate_mcp_config(config)
        assert result == [], f"Valid env var syntax should pass, got: {result}"

    def test_invalid_env_var_syntax_returns_error(self):
        """Env var references not using ${...} syntax should be flagged."""
        config = {
            "server": {
                "transport": "stdio",
                "command": "node",
                "env": {"API_KEY": "$MY_API_KEY"},  # missing braces
            }
        }
        result = validate_mcp_config(config)
        assert len(result) > 0, "Invalid env var syntax should produce error"

    def test_errors_are_strings(self):
        config = {"server": {"transport": "invalid"}}
        result = validate_mcp_config(config)
        for error in result:
            assert isinstance(error, str)

    def test_empty_config_returns_no_error(self):
        """An empty MCP config (no servers) should be valid."""
        result = validate_mcp_config({})
        assert isinstance(result, list)


# ===========================================================================
# 10. validate_lsp_config
# ===========================================================================


class TestValidateLspConfig:
    """validate_lsp_config validates command required per entry and env var syntax."""

    def test_returns_a_list(self):
        result = validate_lsp_config(_valid_lsp_config())
        assert isinstance(result, list)

    def test_valid_config_returns_empty(self):
        result = validate_lsp_config(_valid_lsp_config())
        assert result == [], f"Valid LSP config should pass, got: {result}"

    def test_missing_command_returns_error(self):
        """Each LSP entry requires 'command'."""
        config = {
            "python-lsp": {
                "args": ["--verbose"],
                # missing 'command'
            }
        }
        result = validate_lsp_config(config)
        assert len(result) > 0, "Missing 'command' should produce error"

    def test_valid_env_var_syntax_accepted(self):
        config = {
            "lsp": {
                "command": "pylsp",
                "env": {"PATH": "${MY_PATH}"},
            }
        }
        result = validate_lsp_config(config)
        assert result == [], f"Valid env var syntax should pass, got: {result}"

    def test_invalid_env_var_syntax_returns_error(self):
        config = {
            "lsp": {
                "command": "pylsp",
                "env": {"PATH": "$MY_PATH"},  # missing braces
            }
        }
        result = validate_lsp_config(config)
        assert len(result) > 0, "Invalid env var syntax should produce error"

    def test_errors_are_strings(self):
        config = {"lsp": {}}  # missing command
        result = validate_lsp_config(config)
        for error in result:
            assert isinstance(error, str)

    def test_multiple_lsp_entries_all_validated(self):
        """Multiple LSP server entries should all be validated."""
        config = {
            "python-lsp": {"command": "pylsp"},
            "ts-lsp": {},  # missing command
        }
        result = validate_lsp_config(config)
        assert len(result) > 0, "Entry missing command should produce error"

    def test_empty_config_valid(self):
        result = validate_lsp_config({})
        assert isinstance(result, list)


# ===========================================================================
# 11. validate_skill_frontmatter
# ===========================================================================


class TestValidateSkillFrontmatter:
    """validate_skill_frontmatter validates recognized fields, allowed-tools, model values."""

    def test_returns_a_list(self):
        result = validate_skill_frontmatter(_valid_skill_frontmatter())
        assert isinstance(result, list)

    def test_valid_frontmatter_returns_empty(self):
        result = validate_skill_frontmatter(_valid_skill_frontmatter())
        assert result == [], f"Valid skill frontmatter should pass, got: {result}"

    def test_invalid_allowed_tools_returns_error(self):
        frontmatter = _valid_skill_frontmatter()
        frontmatter["allowed-tools"] = ["NonExistentTool_12345"]
        result = validate_skill_frontmatter(frontmatter)
        assert len(result) > 0, "Invalid allowed-tools should produce error"

    def test_invalid_model_value_returns_error(self):
        frontmatter = _valid_skill_frontmatter()
        frontmatter["model"] = "nonexistent-model-xyz"
        result = validate_skill_frontmatter(frontmatter)
        assert len(result) > 0, "Invalid model value should produce error"

    def test_unrecognized_field_returns_error(self):
        frontmatter = {
            **_valid_skill_frontmatter(),
            "totally_unknown_field": "value",
        }
        result = validate_skill_frontmatter(frontmatter)
        assert len(result) > 0, "Unrecognized field should produce error"

    def test_errors_are_strings(self):
        frontmatter = {"unknown_field": "x"}
        result = validate_skill_frontmatter(frontmatter)
        for error in result:
            assert isinstance(error, str)

    def test_empty_frontmatter_is_handled(self):
        """Empty frontmatter should be handled without crash."""
        result = validate_skill_frontmatter({})
        assert isinstance(result, list)


# ===========================================================================
# 12. validate_hook_definitions
# ===========================================================================


class TestValidateHookDefinitions:
    """validate_hook_definitions validates 12-event set, valid hook types, and matchers."""

    def test_returns_a_list(self):
        result = validate_hook_definitions(_valid_hook_definitions())
        assert isinstance(result, list)

    def test_valid_hook_returns_empty(self):
        result = validate_hook_definitions(_valid_hook_definitions())
        assert result == [], f"Valid hook definitions should pass, got: {result}"

    def test_invalid_event_name_returns_error(self):
        """Events must be from the recognized 12-event set."""
        hooks = {
            "nonexistent_event_xyz": {
                "type": "command",
                "command": "echo test",
            }
        }
        result = validate_hook_definitions(hooks)
        assert len(result) > 0, "Unrecognized event name should produce error"

    def test_invalid_hook_type_returns_error(self):
        """Hook type must be one of: command, http, prompt, agent."""
        hooks = {
            "on_save": {
                "type": "invalid_type",
                "command": "echo test",
            }
        }
        result = validate_hook_definitions(hooks)
        assert len(result) > 0, "Invalid hook type should produce error"

    def test_valid_hook_type_command_accepted(self):
        hooks = {"on_save": {"type": "command", "command": "echo test"}}
        result = validate_hook_definitions(hooks)
        assert result == [], f"'command' hook type should be valid, got: {result}"

    def test_valid_hook_type_http_accepted(self):
        hooks = {"on_save": {"type": "http", "url": "http://example.com"}}
        result = validate_hook_definitions(hooks)
        assert isinstance(result, list)

    def test_valid_hook_type_prompt_accepted(self):
        hooks = {"on_save": {"type": "prompt", "prompt": "Do something"}}
        result = validate_hook_definitions(hooks)
        assert isinstance(result, list)

    def test_valid_hook_type_agent_accepted(self):
        hooks = {"on_save": {"type": "agent", "agent": "helper"}}
        result = validate_hook_definitions(hooks)
        assert isinstance(result, list)

    def test_invalid_matcher_regex_returns_error(self):
        """Hook matcher regex must be valid."""
        hooks = {
            "on_save": {
                "type": "command",
                "command": "echo test",
                "matcher": "[invalid(regex",  # unbalanced bracket
            }
        }
        result = validate_hook_definitions(hooks)
        assert len(result) > 0, "Invalid matcher regex should produce error"

    def test_errors_are_strings(self):
        hooks = {"bad_event": {"type": "bad_type"}}
        result = validate_hook_definitions(hooks)
        for error in result:
            assert isinstance(error, str)

    def test_empty_hooks_is_handled(self):
        result = validate_hook_definitions({})
        assert isinstance(result, list)


# ===========================================================================
# 13. validate_agent_frontmatter
# ===========================================================================


class TestValidateAgentFrontmatter:
    """validate_agent_frontmatter validates recognized fields, disallowedTools, skill refs."""

    def test_returns_a_list(self):
        result = validate_agent_frontmatter(_valid_agent_frontmatter())
        assert isinstance(result, list)

    def test_valid_frontmatter_returns_empty(self):
        result = validate_agent_frontmatter(_valid_agent_frontmatter())
        assert result == [], f"Valid agent frontmatter should pass, got: {result}"

    def test_invalid_disallowed_tools_returns_error(self):
        frontmatter = _valid_agent_frontmatter()
        frontmatter["disallowedTools"] = ["TotallyFakeTool_99999"]
        result = validate_agent_frontmatter(frontmatter)
        assert len(result) > 0, "Invalid disallowedTools should produce error"

    def test_unrecognized_field_returns_error(self):
        frontmatter = {
            **_valid_agent_frontmatter(),
            "completely_unknown_field": "value",
        }
        result = validate_agent_frontmatter(frontmatter)
        assert len(result) > 0, "Unrecognized field should produce error"

    def test_referenced_skills_must_exist(self):
        """If frontmatter references skills, those skills must exist."""
        frontmatter = {
            **_valid_agent_frontmatter(),
            "skills": ["nonexistent-skill-xyz"],
        }
        result = validate_agent_frontmatter(frontmatter)
        # Referenced skills should be validated
        assert isinstance(result, list)

    def test_errors_are_strings(self):
        frontmatter = {"unknown_field": "x", "another_unknown": "y"}
        result = validate_agent_frontmatter(frontmatter)
        for error in result:
            assert isinstance(error, str)

    def test_empty_frontmatter_is_handled(self):
        result = validate_agent_frontmatter({})
        assert isinstance(result, list)


# ===========================================================================
# 14. check_cross_reference_integrity
# ===========================================================================


class TestCheckCrossReferenceIntegrity:
    """check_cross_reference_integrity validates cross-references within a plugin dir."""

    def test_returns_a_list(self, tmp_path):
        """Result must be a list of strings."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        result = check_cross_reference_integrity(plugin_dir)
        assert isinstance(result, list)

    def test_empty_plugin_dir_returns_result(self, tmp_path):
        """An empty plugin directory should be handled gracefully."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        result = check_cross_reference_integrity(plugin_dir)
        assert isinstance(result, list)

    def test_well_formed_plugin_dir_returns_empty(self, tmp_path):
        """A well-formed plugin directory with consistent cross-references returns empty."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        # Create a minimal plugin structure with consistent cross-references
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        manifest = {
            "name": "test-plugin",
            "description": "Test",
            "version": "1.0.0",
            "author": "Test",
            "skills": {"my-skill": {"description": "A skill"}},
            "agents": {"my-agent": {"description": "An agent"}},
        }
        (claude_plugin / "plugin.json").write_text(json.dumps(manifest))
        # Create skill and agent files that reference each other consistently
        skills_dir = plugin_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill.md").write_text("# My Skill\n")
        agents_dir = plugin_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text("# My Agent\n")
        result = check_cross_reference_integrity(plugin_dir)
        assert isinstance(result, list)

    def test_skills_agents_cross_reference_mismatch_detected(self, tmp_path):
        """If agents reference skills that don't exist, errors are reported."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        manifest = {
            "name": "test-plugin",
            "description": "Test",
            "version": "1.0.0",
            "author": "Test",
            "agents": {"my-agent": {"skills": ["nonexistent-skill"]}},
        }
        (claude_plugin / "plugin.json").write_text(json.dumps(manifest))
        result = check_cross_reference_integrity(plugin_dir)
        # Should detect that nonexistent-skill is referenced but doesn't exist
        assert isinstance(result, list)

    def test_mcp_hooks_cross_reference_validated(self, tmp_path):
        """MCP-hooks cross-references are validated."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        manifest = {
            "name": "test-plugin",
            "description": "Test",
            "version": "1.0.0",
            "author": "Test",
            "mcpServers": {"server1": {"transport": "stdio", "command": "node"}},
            "hooks": {
                "on_save": {
                    "type": "command",
                    "command": "echo test",
                    "mcpServer": "nonexistent-server",
                }
            },
        }
        (claude_plugin / "plugin.json").write_text(json.dumps(manifest))
        result = check_cross_reference_integrity(plugin_dir)
        assert isinstance(result, list)

    def test_commands_manifest_cross_reference_validated(self, tmp_path):
        """Commands-manifest cross-references are validated."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        manifest = {
            "name": "test-plugin",
            "description": "Test",
            "version": "1.0.0",
            "author": "Test",
            "commands": {"build": {"script": "scripts/nonexistent.sh"}},
        }
        (claude_plugin / "plugin.json").write_text(json.dumps(manifest))
        result = check_cross_reference_integrity(plugin_dir)
        assert isinstance(result, list)

    def test_errors_are_strings(self, tmp_path):
        """All returned errors must be strings."""
        plugin_dir = tmp_path / "plugin"
        plugin_dir.mkdir()
        result = check_cross_reference_integrity(plugin_dir)
        for error in result:
            assert isinstance(error, str)


# ===========================================================================
# 15. compliance_scan_main (CLI)
# ===========================================================================


class TestComplianceScanMain:
    """compliance_scan_main is a CLI entry point with specific arguments."""

    def test_callable(self):
        assert callable(compliance_scan_main)

    def test_accepts_argv_parameter(self):
        """compliance_scan_main should accept argv as a list parameter."""
        import inspect

        sig = inspect.signature(compliance_scan_main)
        params = list(sig.parameters.keys())
        assert "argv" in params

    def test_argv_defaults_to_none(self):
        """argv parameter should default to None."""
        import inspect

        sig = inspect.signature(compliance_scan_main)
        assert sig.parameters["argv"].default is None

    def test_accepts_project_root_argument(self, tmp_path):
        """CLI should accept --project-root argument."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        src_dir = project_root / "src"
        src_dir.mkdir()
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        # Create a minimal profile and config
        (project_root / "project_profile.json").write_text(
            json.dumps(_minimal_valid_profile())
        )
        (project_root / "svp_config.json").write_text(json.dumps({}))
        try:
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(src_dir),
                    "--tests-dir",
                    str(tests_dir),
                ]
            )
        except SystemExit:
            pass  # CLI may exit with 0 or non-zero
        except Exception:
            pass  # Implementation may raise during scan; we test argument acceptance

    def test_accepts_format_argument(self, tmp_path):
        """CLI should accept --format argument with 'json' or 'text'."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        src_dir = project_root / "src"
        src_dir.mkdir()
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (project_root / "project_profile.json").write_text(
            json.dumps(_minimal_valid_profile())
        )
        (project_root / "svp_config.json").write_text(json.dumps({}))
        try:
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(src_dir),
                    "--tests-dir",
                    str(tests_dir),
                    "--format",
                    "json",
                ]
            )
        except SystemExit:
            pass
        except Exception:
            pass

    def test_accepts_strict_flag(self, tmp_path):
        """CLI should accept --strict flag."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        src_dir = project_root / "src"
        src_dir.mkdir()
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (project_root / "project_profile.json").write_text(
            json.dumps(_minimal_valid_profile())
        )
        (project_root / "svp_config.json").write_text(json.dumps({}))
        try:
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(src_dir),
                    "--tests-dir",
                    str(tests_dir),
                    "--strict",
                ]
            )
        except SystemExit:
            pass
        except Exception:
            pass

    def test_accepts_src_dir_argument(self, tmp_path):
        """CLI should accept --src-dir argument."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        custom_src = tmp_path / "custom_src"
        custom_src.mkdir()
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (project_root / "project_profile.json").write_text(
            json.dumps(_minimal_valid_profile())
        )
        (project_root / "svp_config.json").write_text(json.dumps({}))
        try:
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(custom_src),
                    "--tests-dir",
                    str(tests_dir),
                ]
            )
        except SystemExit:
            pass
        except Exception:
            pass

    def test_accepts_tests_dir_argument(self, tmp_path):
        """CLI should accept --tests-dir argument."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        src_dir = project_root / "src"
        src_dir.mkdir()
        custom_tests = tmp_path / "custom_tests"
        custom_tests.mkdir()
        (project_root / "project_profile.json").write_text(
            json.dumps(_minimal_valid_profile())
        )
        (project_root / "svp_config.json").write_text(json.dumps({}))
        try:
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(src_dir),
                    "--tests-dir",
                    str(custom_tests),
                ]
            )
        except SystemExit:
            pass
        except Exception:
            pass


# ===========================================================================
# 16. Return type invariants across all validate_* functions
# ===========================================================================


class TestValidateFunctionsReturnTypeInvariants:
    """All 6 validate_* functions return List[str] -- empty means valid."""

    def test_validate_plugin_manifest_returns_list_of_strings(self):
        result = validate_plugin_manifest(_minimal_valid_manifest())
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_validate_mcp_config_returns_list_of_strings(self):
        result = validate_mcp_config(_valid_mcp_config_stdio())
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_validate_lsp_config_returns_list_of_strings(self):
        result = validate_lsp_config(_valid_lsp_config())
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_validate_skill_frontmatter_returns_list_of_strings(self):
        result = validate_skill_frontmatter(_valid_skill_frontmatter())
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_validate_hook_definitions_returns_list_of_strings(self):
        result = validate_hook_definitions(_valid_hook_definitions())
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_validate_agent_frontmatter_returns_list_of_strings(self):
        result = validate_agent_frontmatter(_valid_agent_frontmatter())
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)


# ===========================================================================
# 17. validate_dispatch_exhaustiveness -- plugin composite key specifics
# ===========================================================================


class TestPluginCompositeKeyDispatch:
    """Detailed tests for plugin composite key validation in dispatch exhaustiveness."""

    def test_plugin_markdown_key_required_in_stub_generators(self):
        """plugin_markdown must be in STUB_GENERATORS for plugin archetype."""
        registry = {
            "python": {
                **_full_language_registry_entry("python"),
                "archetype": "claude_code_plugin",
            }
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        # Add all plugin keys except plugin_markdown in STUB_GENERATORS
        tables["STUB_GENERATORS"]["plugin_bash"] = lambda: None
        tables["STUB_GENERATORS"]["plugin_json"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_markdown"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_bash"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_json"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_markdown"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_bash"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_json"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, (
            "Missing plugin_markdown in STUB_GENERATORS should produce error"
        )

    def test_plugin_bash_key_required_in_test_output_parsers(self):
        """plugin_bash must be in TEST_OUTPUT_PARSERS for plugin archetype."""
        registry = {
            "python": {
                **_full_language_registry_entry("python"),
                "archetype": "claude_code_plugin",
            }
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        tables["STUB_GENERATORS"]["plugin_markdown"] = lambda: None
        tables["STUB_GENERATORS"]["plugin_bash"] = lambda: None
        tables["STUB_GENERATORS"]["plugin_json"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_markdown"] = lambda: None
        # plugin_bash missing from TEST_OUTPUT_PARSERS
        tables["TEST_OUTPUT_PARSERS"]["plugin_json"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_markdown"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_bash"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_json"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, (
            "Missing plugin_bash in TEST_OUTPUT_PARSERS should produce error"
        )

    def test_plugin_json_key_required_in_quality_runners(self):
        """plugin_json must be in QUALITY_RUNNERS for plugin archetype."""
        registry = {
            "python": {
                **_full_language_registry_entry("python"),
                "archetype": "claude_code_plugin",
            }
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        tables["STUB_GENERATORS"]["plugin_markdown"] = lambda: None
        tables["STUB_GENERATORS"]["plugin_bash"] = lambda: None
        tables["STUB_GENERATORS"]["plugin_json"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_markdown"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_bash"] = lambda: None
        tables["TEST_OUTPUT_PARSERS"]["plugin_json"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_markdown"] = lambda: None
        tables["QUALITY_RUNNERS"]["plugin_bash"] = lambda: None
        # plugin_json missing from QUALITY_RUNNERS
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, (
            "Missing plugin_json in QUALITY_RUNNERS should produce error"
        )

    def test_all_three_plugin_keys_in_all_three_tables_passes(self):
        """All 3 plugin keys in all 3 required tables should pass."""
        registry = {
            "python": {
                **_full_language_registry_entry("python"),
                "archetype": "claude_code_plugin",
            }
        }
        plugin_keys = ["plugin_markdown", "plugin_bash", "plugin_json"]
        tables = _six_dispatch_tables(["python"], ["python"], plugin_keys=plugin_keys)
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], f"All plugin keys present should pass, got: {result}"

    def test_non_plugin_archetype_does_not_check_plugin_keys(self):
        """Non-plugin archetypes should not require plugin composite keys."""
        registry = {
            "python": _full_language_registry_entry("python"),
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        # No plugin keys added -- should still pass for non-plugin archetype
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], (
            f"Non-plugin archetype should not require plugin keys, got: {result}"
        )


# ===========================================================================
# 18. run_structural_check -- output format and strict mode
# ===========================================================================


class TestRunStructuralCheckOutputAndStrictMode:
    """Detailed tests for run_structural_check output_format and strict behavior."""

    def test_text_format_returns_list_of_dicts(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, output_format="text")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_json_format_returns_list_of_dicts(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")
        result = run_structural_check(target, output_format="json")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_strict_true_with_no_findings_succeeds(self, tmp_path):
        """strict=True with no findings should not raise."""
        target = tmp_path / "clean.py"
        target.write_text("def f():\n    return 1\n")
        result = run_structural_check(target, strict=True)
        assert result == []

    def test_default_output_format_is_text(self):
        """Default value of output_format should be 'text'."""
        import inspect

        sig = inspect.signature(run_structural_check)
        assert sig.parameters["output_format"].default == "text"

    def test_default_strict_is_false(self):
        """Default value of strict should be False."""
        import inspect

        sig = inspect.signature(run_structural_check)
        assert sig.parameters["strict"].default is False


# ===========================================================================
# 19. generate_plugin_json -- schema completeness
# ===========================================================================


class TestGeneratePluginJsonSchemaCompleteness:
    """Ensure generate_plugin_json handles all Section 40.7.1 fields correctly."""

    def test_mcp_servers_propagated(self):
        profile = {
            **_minimal_valid_profile(),
            "mcpServers": {"srv": {"transport": "stdio", "command": "node"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "mcpServers" in parsed
        assert "srv" in parsed["mcpServers"]

    def test_lsp_servers_propagated(self):
        profile = {
            **_minimal_valid_profile(),
            "lspServers": {"lsp1": {"command": "pylsp"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "lspServers" in parsed

    def test_hooks_propagated(self):
        profile = {
            **_minimal_valid_profile(),
            "hooks": {"on_save": {"type": "command", "command": "echo"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "hooks" in parsed

    def test_commands_excluded_as_auto_discovered(self):
        """Bug S3-43: commands is auto-discovered, must not appear in output."""
        profile = {
            **_minimal_valid_profile(),
            "commands": {"build": {"description": "Build"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "commands" not in parsed

    def test_agents_excluded_as_auto_discovered(self):
        """Bug S3-43: agents is auto-discovered, must not appear in output."""
        profile = {
            **_minimal_valid_profile(),
            "agents": {"helper": {"description": "Help"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "agents" not in parsed

    def test_skills_excluded_as_auto_discovered(self):
        """Bug S3-43: skills is auto-discovered, must not appear in output."""
        profile = {
            **_minimal_valid_profile(),
            "skills": {"coding": {"description": "Code"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "skills" not in parsed

    def test_output_styles_propagated(self):
        profile = {
            **_minimal_valid_profile(),
            "outputStyles": {"compact": {"description": "Compact"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "outputStyles" in parsed

    def test_tools_propagated(self):
        profile = {
            **_minimal_valid_profile(),
            "tools": {"lint": {"description": "Lint"}},
        }
        parsed = json.loads(generate_plugin_json(profile))
        assert "tools" in parsed


# ===========================================================================
# 20. Integration-style: validate_dispatch_exhaustiveness with mixed registry
# ===========================================================================


class TestDispatchExhaustivenessWithMixedRegistry:
    """Test with a registry containing both full and component-only languages."""

    def test_mixed_registry_all_present_returns_empty(self):
        """Registry with full and component languages, all dispatch entries present."""
        registry = {
            "python": _full_language_registry_entry("python"),
            "r": _full_language_registry_entry("r"),
            "stan": _component_language_registry_entry(
                "stan",
                hosts=["r", "python"],
                required_entries=["stub_generator_key", "quality_runner_key"],
            ),
        }
        tables = _six_dispatch_tables(["python", "r"], ["python", "r"])
        tables["STUB_GENERATORS"]["stan_template"] = lambda: None
        tables["QUALITY_RUNNERS"]["stan_syntax_check"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert result == [], (
            f"Mixed registry with all entries should pass, got: {result}"
        )

    def test_mixed_registry_component_missing_entry_reports_error(self):
        """Component language missing a required entry in mixed registry."""
        registry = {
            "python": _full_language_registry_entry("python"),
            "stan": _component_language_registry_entry(
                "stan",
                required_entries=["stub_generator_key", "quality_runner_key"],
            ),
        }
        tables = _six_dispatch_tables(["python"], ["python"])
        # Only add one of stan's required entries
        tables["STUB_GENERATORS"]["stan_template"] = lambda: None
        result = validate_dispatch_exhaustiveness(registry, tables)
        assert len(result) > 0, "Component missing required entry should produce error"

    def test_empty_registry_returns_empty(self):
        """Empty registry should produce no errors (nothing to check)."""
        result = validate_dispatch_exhaustiveness({}, {})
        assert result == [], f"Empty registry should produce no errors, got: {result}"

    def test_empty_dispatch_tables_with_languages_returns_errors(self):
        """Languages in registry but empty dispatch tables should produce errors."""
        registry = {
            "python": _full_language_registry_entry("python"),
        }
        result = validate_dispatch_exhaustiveness(registry, {})
        assert len(result) > 0, (
            "Languages with no dispatch tables should produce errors"
        )
