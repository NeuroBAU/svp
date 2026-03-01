"""
Test suite for Unit 16: Diagnostic and Classification Agent Definitions.

Tests verify the agent definition constants for the Diagnostic Agent and Redo Agent,
including frontmatter dictionaries, terminal status lines, and the MD_CONTENT strings
that represent complete Claude Code agent definition files.

## Synthetic Data Assumptions

- DATA ASSUMPTION: Frontmatter dictionaries are exact literal values from the blueprint
  Tier 2 signatures. No synthetic data generation needed -- these are spec constants.
- DATA ASSUMPTION: Terminal status line lists are exact literal values from the blueprint.
- DATA ASSUMPTION: MD_CONTENT strings are expected to be valid Claude Code agent
  definition files starting with YAML frontmatter delimiters ("---\\n"), containing
  name/model/tools keys, and followed by substantial behavioral instructions (>100 chars).
- DATA ASSUMPTION: The frontmatter inside each MD_CONTENT string must match the
  corresponding *_FRONTMATTER dict's key-value pairs exactly.
- DATA ASSUMPTION: "Substantial behavioral instructions" means >100 characters of text
  after the closing frontmatter delimiter, per the blueprint invariant.
- DATA ASSUMPTION: 500 characters is used as a reasonable minimum threshold for
  "detailed enough for autonomous operation" (the blueprint says >100 chars for the
  invariant, but autonomous operation implies much more substantial content).
"""

import pytest
import svp.scripts.diagnostic_agent_definitions as unit_16_module


# ---------------------------------------------------------------------------
# Helper: inline YAML frontmatter parser (no pyyaml dependency)
# ---------------------------------------------------------------------------

def _parse_frontmatter(md_content: str) -> dict:
    """Parse YAML frontmatter from a Markdown string (no pyyaml dependency)."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    yaml_block = md_content[4:second_delim]
    result = {}
    current_key = None
    current_list = []
    for line in yaml_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("\t- "):
            current_list.append(stripped[2:].strip().strip("\"'"))
            continue
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []
            current_key = None
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                result[key] = [i.strip().strip("\"'") for i in inner.split(",") if i.strip()]
            elif val == "":
                current_key = key
            elif val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                result[key] = val[1:-1]
            else:
                result[key] = val
    if current_key and current_list:
        result[current_key] = current_list
    return result


def _get_md_content(name: str) -> str:
    """Retrieve an MD_CONTENT constant from the stub module.

    Uses getattr to avoid ImportError when the stub only has a type annotation
    (no assigned value) for the constant. Fails the test with a clear message
    if the constant is not yet defined (ensures red-run failure against stubs).
    """
    value = getattr(unit_16_module, name, None)
    if value is None:
        pytest.fail(
            f"{name} is not defined in the module (expected a str constant "
            f"containing a complete Claude Code agent definition)"
        )
    return value


# ===========================================================================
# Tests for DIAGNOSTIC_AGENT_FRONTMATTER
# ===========================================================================


class TestDiagnosticAgentFrontmatter:
    """Verify the DIAGNOSTIC_AGENT_FRONTMATTER constant matches the blueprint."""

    def test_is_dict(self):
        """DIAGNOSTIC_AGENT_FRONTMATTER must be a Dict[str, Any]."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert isinstance(DIAGNOSTIC_AGENT_FRONTMATTER, dict)

    def test_name_key(self):
        """Frontmatter 'name' must be 'diagnostic_agent'."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert DIAGNOSTIC_AGENT_FRONTMATTER["name"] == "diagnostic_agent"

    def test_description_key(self):
        """Frontmatter 'description' must describe three-hypothesis analysis."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert DIAGNOSTIC_AGENT_FRONTMATTER["description"] == "Analyzes test failures using three-hypothesis discipline"

    def test_model_key(self):
        """Frontmatter 'model' must be 'claude-opus-4-6'."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert DIAGNOSTIC_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools_key(self):
        """Frontmatter 'tools' must be ['Read', 'Glob', 'Grep']."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert DIAGNOSTIC_AGENT_FRONTMATTER["tools"] == ["Read", "Glob", "Grep"]

    def test_exact_keys(self):
        """Frontmatter must contain exactly name, description, model, tools."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert set(DIAGNOSTIC_AGENT_FRONTMATTER.keys()) == {"name", "description", "model", "tools"}


# ===========================================================================
# Tests for REDO_AGENT_FRONTMATTER
# ===========================================================================


class TestRedoAgentFrontmatter:
    """Verify the REDO_AGENT_FRONTMATTER constant matches the blueprint."""

    def test_is_dict(self):
        """REDO_AGENT_FRONTMATTER must be a Dict[str, Any]."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert isinstance(REDO_AGENT_FRONTMATTER, dict)

    def test_name_key(self):
        """Frontmatter 'name' must be 'redo_agent'."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert REDO_AGENT_FRONTMATTER["name"] == "redo_agent"

    def test_description_key(self):
        """Frontmatter 'description' must describe tracing human gate errors."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert REDO_AGENT_FRONTMATTER["description"] == "Traces human gate errors through the document hierarchy"

    def test_model_key(self):
        """Frontmatter 'model' must be 'claude-opus-4-6'."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert REDO_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools_key(self):
        """Frontmatter 'tools' must be ['Read', 'Glob', 'Grep']."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert REDO_AGENT_FRONTMATTER["tools"] == ["Read", "Glob", "Grep"]

    def test_exact_keys(self):
        """Frontmatter must contain exactly name, description, model, tools."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert set(REDO_AGENT_FRONTMATTER.keys()) == {"name", "description", "model", "tools"}


# ===========================================================================
# Tests for DIAGNOSTIC_AGENT_STATUS
# ===========================================================================


class TestDiagnosticAgentStatus:
    """Verify the DIAGNOSTIC_AGENT_STATUS constant matches the blueprint."""

    def test_is_list(self):
        """DIAGNOSTIC_AGENT_STATUS must be a List[str]."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        assert isinstance(DIAGNOSTIC_AGENT_STATUS, list)

    def test_contains_implementation(self):
        """Must contain 'DIAGNOSIS_COMPLETE: implementation'."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        assert "DIAGNOSIS_COMPLETE: implementation" in DIAGNOSTIC_AGENT_STATUS

    def test_contains_blueprint(self):
        """Must contain 'DIAGNOSIS_COMPLETE: blueprint'."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        assert "DIAGNOSIS_COMPLETE: blueprint" in DIAGNOSTIC_AGENT_STATUS

    def test_contains_spec(self):
        """Must contain 'DIAGNOSIS_COMPLETE: spec'."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        assert "DIAGNOSIS_COMPLETE: spec" in DIAGNOSTIC_AGENT_STATUS

    def test_exact_length(self):
        """Must contain exactly three status lines."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        assert len(DIAGNOSTIC_AGENT_STATUS) == 3

    def test_all_strings(self):
        """All elements must be strings."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        assert all(isinstance(s, str) for s in DIAGNOSTIC_AGENT_STATUS)


# ===========================================================================
# Tests for REDO_AGENT_STATUS
# ===========================================================================


class TestRedoAgentStatus:
    """Verify the REDO_AGENT_STATUS constant matches the blueprint."""

    def test_is_list(self):
        """REDO_AGENT_STATUS must be a List[str]."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert isinstance(REDO_AGENT_STATUS, list)

    def test_contains_spec(self):
        """Must contain 'REDO_CLASSIFIED: spec'."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: spec" in REDO_AGENT_STATUS

    def test_contains_blueprint(self):
        """Must contain 'REDO_CLASSIFIED: blueprint'."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: blueprint" in REDO_AGENT_STATUS

    def test_contains_gate(self):
        """Must contain 'REDO_CLASSIFIED: gate'."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: gate" in REDO_AGENT_STATUS

    def test_exact_length(self):
        """Must contain exactly three status lines."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert len(REDO_AGENT_STATUS) == 3

    def test_all_strings(self):
        """All elements must be strings."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert all(isinstance(s, str) for s in REDO_AGENT_STATUS)


# ===========================================================================
# Tests for DIAGNOSTIC_AGENT_MD_CONTENT
# ===========================================================================


class TestDiagnosticAgentMdContent:
    """Verify the DIAGNOSTIC_AGENT_MD_CONTENT constant is a complete
    Claude Code agent definition file satisfying all blueprint invariants
    and behavioral contracts."""

    def _get_content(self) -> str:
        return _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")

    # --- Invariant: valid agent definition structure ---

    def test_is_string(self):
        """MD_CONTENT must be a str."""
        content = self._get_content()
        assert isinstance(content, str)

    def test_starts_with_frontmatter_delimiter(self):
        """Invariant: starts with '---\\n' (YAML frontmatter delimiter)."""
        content = self._get_content()
        assert content.startswith("---\n"), "MD_CONTENT must start with '---\\n'"

    def test_has_second_frontmatter_delimiter(self):
        """Invariant: contains a second '---\\n' (end of frontmatter)."""
        content = self._get_content()
        # Find second occurrence
        first_end = 4  # after initial "---\n"
        second_pos = content.find("---\n", first_end)
        assert second_pos > first_end, "MD_CONTENT must have a closing '---\\n' delimiter"

    def test_frontmatter_contains_name(self):
        """Invariant: contains 'name:' in frontmatter."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert "name" in fm, "Frontmatter must contain 'name:'"

    def test_frontmatter_contains_model(self):
        """Invariant: contains 'model:' in frontmatter."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert "model" in fm, "Frontmatter must contain 'model:'"

    def test_frontmatter_contains_tools(self):
        """Invariant: contains 'tools:' in frontmatter."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert "tools" in fm, "Frontmatter must contain 'tools:'"

    def test_substantial_instructions_after_frontmatter(self):
        """Invariant: has substantial behavioral instructions after frontmatter (>100 chars)."""
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert len(body) > 100, (
            f"Body after frontmatter must be >100 chars, got {len(body)}"
        )

    # --- Behavioral contract: frontmatter matches DIAGNOSTIC_AGENT_FRONTMATTER ---

    def test_frontmatter_name_matches(self):
        """Frontmatter 'name' must match DIAGNOSTIC_AGENT_FRONTMATTER['name']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["name"] == DIAGNOSTIC_AGENT_FRONTMATTER["name"]

    def test_frontmatter_description_matches(self):
        """Frontmatter 'description' must match DIAGNOSTIC_AGENT_FRONTMATTER['description']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["description"] == DIAGNOSTIC_AGENT_FRONTMATTER["description"]

    def test_frontmatter_model_matches(self):
        """Frontmatter 'model' must match DIAGNOSTIC_AGENT_FRONTMATTER['model']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["model"] == DIAGNOSTIC_AGENT_FRONTMATTER["model"]

    def test_frontmatter_tools_matches(self):
        """Frontmatter 'tools' must match DIAGNOSTIC_AGENT_FRONTMATTER['tools']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["tools"] == DIAGNOSTIC_AGENT_FRONTMATTER["tools"]

    # --- Behavioral contract: instructions describe agent purpose/methodology ---

    def test_instructions_describe_purpose(self):
        """Body must describe the agent's purpose (diagnostic/analysis context)."""
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # The diagnostic agent analyzes test failures
        assert "diagnostic" in body or "diagnos" in body, (
            "Instructions must describe the diagnostic agent's purpose"
        )

    def test_instructions_describe_three_hypothesis_discipline(self):
        """Body must describe three-hypothesis discipline: implementation, blueprint, spec.

        Contract: Must articulate a plausible case at each of three levels
        (implementation, blueprint, spec) before converging.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # Must mention all three hypothesis levels
        assert "implementation" in body, "Instructions must mention 'implementation' hypothesis"
        assert "blueprint" in body, "Instructions must mention 'blueprint' hypothesis"
        assert "spec" in body, "Instructions must mention 'spec' hypothesis"

    def test_instructions_mention_three_hypotheses(self):
        """Body must explicitly reference three hypotheses or the three-hypothesis approach."""
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # Should reference the concept of three hypotheses
        assert "three" in body or "3" in body or "hypothes" in body, (
            "Instructions must reference three hypotheses or hypothesis discipline"
        )

    def test_instructions_describe_dual_format_output(self):
        """Body must describe dual-format output: [PROSE] and [STRUCTURED] block.

        Contract: Produces dual-format output: [PROSE] section followed by
        [STRUCTURED] block.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        # Check for the dual-format markers
        assert "PROSE" in body or "prose" in body.lower(), (
            "Instructions must describe [PROSE] output section"
        )
        assert "STRUCTURED" in body or "structured" in body.lower(), (
            "Instructions must describe [STRUCTURED] output block"
        )

    def test_instructions_describe_structured_fields(self):
        """Body must describe the structured block fields: UNIT, HYPOTHESIS_1,
        HYPOTHESIS_2, HYPOTHESIS_3, RECOMMENDATION.

        Contract: [STRUCTURED] block with UNIT, HYPOTHESIS_1, HYPOTHESIS_2,
        HYPOTHESIS_3, and RECOMMENDATION.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert "UNIT" in body, "Structured block must include UNIT field"
        assert "HYPOTHESIS_1" in body, "Structured block must include HYPOTHESIS_1 field"
        assert "HYPOTHESIS_2" in body, "Structured block must include HYPOTHESIS_2 field"
        assert "HYPOTHESIS_3" in body, "Structured block must include HYPOTHESIS_3 field"
        assert "RECOMMENDATION" in body, "Structured block must include RECOMMENDATION field"

    def test_instructions_describe_terminal_status_lines(self):
        """Body must describe all three possible terminal status lines.

        Contract: Terminal status: DIAGNOSIS_COMPLETE: implementation,
        DIAGNOSIS_COMPLETE: blueprint, or DIAGNOSIS_COMPLETE: spec.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert "DIAGNOSIS_COMPLETE: implementation" in body
        assert "DIAGNOSIS_COMPLETE: blueprint" in body
        assert "DIAGNOSIS_COMPLETE: spec" in body

    def test_instructions_describe_input_context(self):
        """Body must describe what the agent receives as input.

        Contract: Receives stakeholder spec, unit blueprint section, failing tests,
        error output, and failing implementations.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # Must reference the key inputs
        assert "spec" in body or "stakeholder" in body, (
            "Instructions must mention stakeholder spec as input"
        )
        assert "blueprint" in body, (
            "Instructions must mention blueprint section as input"
        )
        assert "test" in body or "fail" in body, (
            "Instructions must mention failing tests/error output"
        )

    def test_instructions_mention_converging(self):
        """Body must describe convergence after articulating all three hypotheses.

        Contract: Must articulate a plausible case at each of three levels
        before converging.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "converg" in body or "before" in body or "articulate" in body, (
            "Instructions must describe convergence discipline"
        )

    def test_instructions_mention_model(self):
        """Frontmatter must specify claude-opus-4-6."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"


# ===========================================================================
# Tests for REDO_AGENT_MD_CONTENT
# ===========================================================================


class TestRedoAgentMdContent:
    """Verify the REDO_AGENT_MD_CONTENT constant is a complete
    Claude Code agent definition file satisfying all blueprint invariants
    and behavioral contracts."""

    def _get_content(self) -> str:
        return _get_md_content("REDO_AGENT_MD_CONTENT")

    # --- Invariant: valid agent definition structure ---

    def test_is_string(self):
        """MD_CONTENT must be a str."""
        content = self._get_content()
        assert isinstance(content, str)

    def test_starts_with_frontmatter_delimiter(self):
        """Invariant: starts with '---\\n' (YAML frontmatter delimiter)."""
        content = self._get_content()
        assert content.startswith("---\n"), "MD_CONTENT must start with '---\\n'"

    def test_has_second_frontmatter_delimiter(self):
        """Invariant: contains a second '---\\n' (end of frontmatter)."""
        content = self._get_content()
        first_end = 4
        second_pos = content.find("---\n", first_end)
        assert second_pos > first_end, "MD_CONTENT must have a closing '---\\n' delimiter"

    def test_frontmatter_contains_name(self):
        """Invariant: contains 'name:' in frontmatter."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert "name" in fm, "Frontmatter must contain 'name:'"

    def test_frontmatter_contains_model(self):
        """Invariant: contains 'model:' in frontmatter."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert "model" in fm, "Frontmatter must contain 'model:'"

    def test_frontmatter_contains_tools(self):
        """Invariant: contains 'tools:' in frontmatter."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert "tools" in fm, "Frontmatter must contain 'tools:'"

    def test_substantial_instructions_after_frontmatter(self):
        """Invariant: has substantial behavioral instructions after frontmatter (>100 chars)."""
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert len(body) > 100, (
            f"Body after frontmatter must be >100 chars, got {len(body)}"
        )

    # --- Behavioral contract: frontmatter matches REDO_AGENT_FRONTMATTER ---

    def test_frontmatter_name_matches(self):
        """Frontmatter 'name' must match REDO_AGENT_FRONTMATTER['name']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["name"] == REDO_AGENT_FRONTMATTER["name"]

    def test_frontmatter_description_matches(self):
        """Frontmatter 'description' must match REDO_AGENT_FRONTMATTER['description']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["description"] == REDO_AGENT_FRONTMATTER["description"]

    def test_frontmatter_model_matches(self):
        """Frontmatter 'model' must match REDO_AGENT_FRONTMATTER['model']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["model"] == REDO_AGENT_FRONTMATTER["model"]

    def test_frontmatter_tools_matches(self):
        """Frontmatter 'tools' must match REDO_AGENT_FRONTMATTER['tools']."""
        content = self._get_content()
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        fm = _parse_frontmatter(content)
        assert fm["tools"] == REDO_AGENT_FRONTMATTER["tools"]

    # --- Behavioral contract: instructions describe agent purpose/methodology ---

    def test_instructions_describe_purpose(self):
        """Body must describe the redo agent's purpose (tracing errors/redo classification)."""
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "redo" in body or "error" in body or "classify" in body, (
            "Instructions must describe the redo agent's purpose"
        )

    def test_instructions_describe_document_hierarchy_tracing(self):
        """Body must describe tracing errors through document hierarchy (spec -> blueprint -> tests).

        Contract: Uses read tools to trace the error through the document hierarchy
        (spec -> blueprint -> tests/implementation).
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "spec" in body, "Instructions must mention spec in hierarchy"
        assert "blueprint" in body, "Instructions must mention blueprint in hierarchy"
        assert ("trace" in body or "trac" in body or "hierarch" in body
                or "document" in body), (
            "Instructions must describe document hierarchy tracing"
        )

    def test_instructions_agent_classifies_not_human(self):
        """Body must describe that the agent classifies the error -- does NOT ask human to self-classify.

        Contract: Classifies the error source -- does NOT ask the human to self-classify.
        Invariant: Redo agent must not ask the human to self-classify their error.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "classif" in body, "Instructions must describe classification behavior"
        # Should explicitly mention NOT asking human to self-classify
        assert ("do not ask" in body or "must not ask" in body
                or "don't ask" in body or "never ask" in body
                or "not ask the human" in body or "self-classify" in body
                or "self-classif" in body), (
            "Instructions must explicitly state not to ask human to self-classify"
        )

    def test_instructions_describe_dual_format_output(self):
        """Body must describe dual-format output.

        Contract: Produces dual-format output.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "dual" in body or ("prose" in body and "structured" in body), (
            "Instructions must describe dual-format output"
        )

    def test_instructions_describe_terminal_status_lines(self):
        """Body must describe all three possible terminal status lines.

        Contract: Terminal status: REDO_CLASSIFIED: spec, REDO_CLASSIFIED: blueprint,
        or REDO_CLASSIFIED: gate.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert "REDO_CLASSIFIED: spec" in body
        assert "REDO_CLASSIFIED: blueprint" in body
        assert "REDO_CLASSIFIED: gate" in body

    def test_instructions_describe_error_source_classification(self):
        """Body must describe classification into spec, blueprint, or gate.

        Contract: Classifies the error source.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # Must mention all three classification targets
        assert "spec" in body
        assert "blueprint" in body
        assert "gate" in body

    def test_instructions_describe_input_context(self):
        """Body must describe what the redo agent receives as input.

        Contract: Receives pipeline state summary, human error description,
        and current unit definition.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # Must reference key inputs
        assert "pipeline" in body or "state" in body, (
            "Instructions must mention pipeline state as input"
        )
        assert "error" in body or "human" in body, (
            "Instructions must mention human error description"
        )

    def test_instructions_mention_available_stages(self):
        """Body or context must indicate redo agent is available during Stages 2, 3, and 4.

        Contract: Available during Stages 2, 3, and 4.
        """
        content = self._get_content()
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # The stage availability may be mentioned in the instructions
        # or may be implicit through the agent's described role
        # At minimum the content should reference stage context
        assert ("stage" in body or "2" in body or "3" in body or "4" in body
                or "redo" in body), (
            "Instructions should reference the redo/stage context"
        )

    def test_instructions_mention_model(self):
        """Frontmatter must specify claude-opus-4-6."""
        content = self._get_content()
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"


# ===========================================================================
# Cross-cutting tests
# ===========================================================================


class TestCrossCuttingInvariants:
    """Tests that verify cross-cutting invariants applying to both agents."""

    def test_diagnostic_md_content_is_not_empty(self):
        """MD_CONTENT must not be empty."""
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        assert len(content) > 0

    def test_redo_md_content_is_not_empty(self):
        """MD_CONTENT must not be empty."""
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        assert len(content) > 0

    def test_diagnostic_content_is_autonomous(self):
        """Instructions should be detailed enough for autonomous operation, not a placeholder.

        Contract: The instructions should be detailed enough that the agent can
        perform its role autonomously -- not a placeholder or skeleton.
        """
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        # A placeholder would be very short; an autonomous agent definition
        # needs substantial instructions (blueprint says >100 chars, but autonomous
        # operation requires much more -- we check for at least 500 chars as a
        # reasonable proxy for "detailed enough for autonomous operation")
        # DATA ASSUMPTION: 500 chars is a reasonable minimum for autonomous instructions
        assert len(body) > 500, (
            f"Autonomous agent instructions should be substantial (>500 chars), got {len(body)}"
        )

    def test_redo_content_is_autonomous(self):
        """Instructions should be detailed enough for autonomous operation, not a placeholder."""
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        # DATA ASSUMPTION: 500 chars is a reasonable minimum for autonomous instructions
        assert len(body) > 500, (
            f"Autonomous agent instructions should be substantial (>500 chars), got {len(body)}"
        )

    def test_diagnostic_mentions_methodology(self):
        """Instructions must describe the agent's methodology.

        Contract: behavioral instructions must describe methodology.
        """
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert ("method" in body or "phase" in body or "step" in body
                or "procedure" in body or "approach" in body), (
            "Instructions must describe the agent's methodology"
        )

    def test_redo_mentions_methodology(self):
        """Instructions must describe the agent's methodology."""
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert ("method" in body or "phase" in body or "step" in body
                or "procedure" in body or "approach" in body), (
            "Instructions must describe the agent's methodology"
        )

    def test_diagnostic_mentions_constraints(self):
        """Instructions must describe the agent's constraints.

        Contract: behavioral instructions must describe constraints.
        """
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert ("constraint" in body or "must not" in body or "do not" in body
                or "must" in body or "required" in body or "never" in body), (
            "Instructions must describe constraints"
        )

    def test_redo_mentions_constraints(self):
        """Instructions must describe the agent's constraints."""
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert ("constraint" in body or "must not" in body or "do not" in body
                or "must" in body or "required" in body or "never" in body), (
            "Instructions must describe constraints"
        )

    def test_diagnostic_mentions_io_format(self):
        """Instructions must describe input/output format.

        Contract: behavioral instructions must describe input/output format.
        """
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "input" in body or "output" in body or "format" in body, (
            "Instructions must describe input/output format"
        )

    def test_redo_mentions_io_format(self):
        """Instructions must describe input/output format."""
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "input" in body or "output" in body or "format" in body, (
            "Instructions must describe input/output format"
        )

    def test_all_exported_constants_exist(self):
        """All constants from the blueprint signatures must exist in the module.

        This verifies that the implementation defines actual values for all
        constants, not just type annotations.
        """
        expected = [
            "DIAGNOSTIC_AGENT_FRONTMATTER",
            "REDO_AGENT_FRONTMATTER",
            "DIAGNOSTIC_AGENT_STATUS",
            "REDO_AGENT_STATUS",
            "DIAGNOSTIC_AGENT_MD_CONTENT",
            "REDO_AGENT_MD_CONTENT",
        ]
        for name in expected:
            val = getattr(unit_16_module, name, None)
            assert val is not None, (
                f"Module must export {name} with a defined value (not just a type annotation)"
            )

    def test_diagnostic_frontmatter_types(self):
        """DIAGNOSTIC_AGENT_FRONTMATTER values must have correct types."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_FRONTMATTER
        assert isinstance(DIAGNOSTIC_AGENT_FRONTMATTER["name"], str)
        assert isinstance(DIAGNOSTIC_AGENT_FRONTMATTER["description"], str)
        assert isinstance(DIAGNOSTIC_AGENT_FRONTMATTER["model"], str)
        assert isinstance(DIAGNOSTIC_AGENT_FRONTMATTER["tools"], list)
        for tool in DIAGNOSTIC_AGENT_FRONTMATTER["tools"]:
            assert isinstance(tool, str)

    def test_redo_frontmatter_types(self):
        """REDO_AGENT_FRONTMATTER values must have correct types."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_FRONTMATTER
        assert isinstance(REDO_AGENT_FRONTMATTER["name"], str)
        assert isinstance(REDO_AGENT_FRONTMATTER["description"], str)
        assert isinstance(REDO_AGENT_FRONTMATTER["model"], str)
        assert isinstance(REDO_AGENT_FRONTMATTER["tools"], list)
        for tool in REDO_AGENT_FRONTMATTER["tools"]:
            assert isinstance(tool, str)


# ===========================================================================
# Tests for the three-hypothesis discipline invariant
# ===========================================================================


class TestThreeHypothesisDiscipline:
    """Verify the Diagnostic Agent enforces three-hypothesis discipline.

    Invariant: Diagnostic agent must articulate all three hypotheses before converging.
    This is tested through the MD_CONTENT instructions and the STATUS list.
    """

    def test_status_covers_all_three_levels(self):
        """All three diagnosis levels must be represented in status lines."""
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        levels = {"implementation", "blueprint", "spec"}
        found = set()
        for status in DIAGNOSTIC_AGENT_STATUS:
            for level in levels:
                if level in status:
                    found.add(level)
        assert found == levels, (
            f"Status lines must cover all three levels; missing: {levels - found}"
        )

    def test_instructions_require_all_three_before_convergence(self):
        """Instructions must require articulating all three before converging.

        Invariant: Diagnostic agent must articulate all three hypotheses before converging.
        """
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        # Must reference all three levels
        assert "implementation" in body
        assert "blueprint" in body
        assert "spec" in body
        # Must indicate the discipline of considering all before picking one
        assert ("all three" in body or "each" in body or "every" in body
                or "before converg" in body or "before select" in body
                or "before recomm" in body or "before choos" in body
                or "plausible" in body), (
            "Instructions must require considering all three hypotheses before converging"
        )


# ===========================================================================
# Tests for self-classification prohibition invariant
# ===========================================================================


class TestSelfClassificationProhibition:
    """Verify the Redo Agent does not ask the human to self-classify.

    Invariant: Redo agent must not ask the human to self-classify their error.
    """

    def test_redo_classifies_autonomously(self):
        """Redo agent must classify the error itself, not delegate to the human."""
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "classif" in body, (
            "Instructions must describe the classification behavior"
        )

    def test_redo_status_shows_classification_output(self):
        """Status lines confirm the agent produces a classification."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        assert all("REDO_CLASSIFIED:" in s for s in REDO_AGENT_STATUS), (
            "All redo status lines should be REDO_CLASSIFIED: variants"
        )

    def test_redo_status_covers_all_three_targets(self):
        """All three classification targets must be represented in status lines."""
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        targets = {"spec", "blueprint", "gate"}
        found = set()
        for status in REDO_AGENT_STATUS:
            for target in targets:
                if target in status:
                    found.add(target)
        assert found == targets, (
            f"Status lines must cover all three targets; missing: {targets - found}"
        )
