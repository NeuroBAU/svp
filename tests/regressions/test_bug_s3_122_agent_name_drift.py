"""Regression tests for Bug S3-122: Agent frontmatter name drift.

Plugin agent files shipped with hyphenated YAML frontmatter `name` values
(e.g., `name: oracle-agent`) while the underlying filenames used underscores
(`oracle_agent.md`). Claude Code's plugin loader uses the frontmatter `name`
field as the agent registration identifier, so the registered subagent_type
became `svp:oracle-agent` while every internal SVP reference (PHASE_TO_AGENT,
AGENT_STATUS_LINES, action block agent_type, prepare_task --agent flag, etc.)
used the underscored form `oracle_agent`. The orchestrator was implicitly
translating between the two on every agent invocation — undocumented and
fragile.

The fix removes the `_` -> `-` transformation in `src/unit_23/stub.py` (lines
837 and 1121) so the frontmatter `name` equals the filename stem verbatim.
After the fix:
  - filename:        oracle_agent.md
  - frontmatter:     name: oracle_agent
  - registered:      svp:oracle_agent
  - internal refs:   oracle_agent (matches everywhere)

These tests lock all four sides of the chain.

Companion to test_bug_s3_121_command_double_prefix.py — same bug family,
different surface (agents vs commands).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# S3-103: tests must not import from src.unit_*.stub. Import from the derived
# routing module instead. PHASE_TO_AGENT and the action-block builder live
# in scripts/routing.py which is derived from src/unit_14/stub.py.
from routing import PHASE_TO_AGENT


_REPO_ROOT_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "svp" / "agents",
    Path(__file__).resolve().parents[3] / "svp2.2-pass2-repo" / "svp" / "agents",
]


def _resolve_agents_dir() -> Path:
    """Find the deployed `svp/agents/` directory.

    The test runs from either the workspace or the repo. In the workspace,
    there is no `svp/agents/` (the workspace is the source-of-truth tree;
    the deployed plugin lives in the sibling repo). In the repo, `svp/agents/`
    exists at `<repo_root>/svp/agents/`. Try both.
    """
    for candidate in _REPO_ROOT_CANDIDATES:
        if candidate.is_dir():
            return candidate
    pytest.skip(
        "Deployed agents/ directory not found from either workspace or repo. "
        "Tried: " + ", ".join(str(c) for c in _REPO_ROOT_CANDIDATES)
    )


_FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


def _read_frontmatter_name(path: Path) -> str:
    """Extract the YAML frontmatter `name` field from an agent file."""
    text = path.read_text()
    head = text.split("\n---", 2)
    if len(head) < 2 or not text.startswith("---"):
        raise AssertionError(f"{path.name}: no YAML frontmatter found")
    fm_block = head[0].lstrip("-").strip() + "\n" + head[1].split("---")[0]
    match = _FRONTMATTER_NAME_RE.search(fm_block)
    if not match:
        raise AssertionError(
            f"{path.name}: no `name:` field in frontmatter\n---\n{fm_block}\n---"
        )
    return match.group(1)


class TestAgentFrontmatterMatchesFilename:
    """Frontmatter `name` must equal the filename stem verbatim (Bug S3-122)."""

    def test_agent_frontmatter_name_matches_filename_stem(self):
        """For every agent file, frontmatter `name` == filename stem (no transformation)."""
        agents_dir = _resolve_agents_dir()
        mismatches = []
        for agent_file in sorted(agents_dir.glob("*.md")):
            stem = agent_file.stem
            name = _read_frontmatter_name(agent_file)
            if name != stem:
                mismatches.append(
                    f"  {agent_file.name}: frontmatter name {name!r} != "
                    f"filename stem {stem!r}"
                )
        assert not mismatches, (
            "Agent frontmatter `name` must equal the filename stem verbatim "
            "(Bug S3-122 drift detector). Claude Code uses the frontmatter "
            "`name` field as the agent registration identifier; any "
            "transformation creates drift between the registered subagent_type "
            "and the underscored form used everywhere in the SVP codebase. "
            "Mismatches:\n" + "\n".join(mismatches)
        )


class TestAgentFrontmatterNoSeparatorTransformation:
    """Negative sentinel: no agent frontmatter `name` may contain a hyphen (Bug S3-122)."""

    def test_agent_frontmatter_name_has_no_hyphen(self):
        """No frontmatter `name` value contains '-'.

        The fix removed `name = stem.replace('_', '-')` from
        src/unit_23/stub.py. If a future commit re-introduces the
        transformation (or any other source-to-target identifier conversion
        that produces hyphenated names), this assertion fires immediately.
        """
        agents_dir = _resolve_agents_dir()
        offenders = []
        for agent_file in sorted(agents_dir.glob("*.md")):
            name = _read_frontmatter_name(agent_file)
            if "-" in name:
                offenders.append(f"  {agent_file.name}: name = {name!r}")
        assert not offenders, (
            "Agent frontmatter `name` values must not contain '-' "
            "(Bug S3-122 negative sentinel). The previous unit_23 generator "
            "transformed underscores to hyphens; the fix removed that "
            "transformation. A re-introduction of this drift would break "
            "the orchestrator's ability to reference agents by their "
            "internal underscored identifiers. Offenders:\n"
            + "\n".join(offenders)
        )


class TestPhaseToAgentReferencesExistingAgents:
    """PHASE_TO_AGENT values must be deployed agent filename stems (Bug S3-122)."""

    def test_phase_to_agent_values_match_agent_filenames(self):
        """Every PHASE_TO_AGENT value is the filename stem of an existing agent file.

        This is the routing-side lock for the agent identifier chain. If the
        unit_23 generator drifts again or the agent files are renamed, this
        assertion fires before the orchestrator tries to spawn a missing
        agent at runtime.
        """
        agents_dir = _resolve_agents_dir()
        existing_stems = {p.stem for p in agents_dir.glob("*.md")}
        offenders = []
        for phase, agent_type in PHASE_TO_AGENT.items():
            if agent_type not in existing_stems:
                offenders.append(
                    f"  phase={phase!r} -> agent_type={agent_type!r} "
                    f"(no svp/agents/{agent_type}.md)"
                )
        assert not offenders, (
            "PHASE_TO_AGENT values must correspond to deployed agent filenames "
            "(Bug S3-122 chain-lock). Existing agent stems: "
            f"{sorted(existing_stems)}. Offenders:\n" + "\n".join(offenders)
        )


class TestActionBlockAgentTypesMatchAgentFilenames:
    """invoke_agent action block agent_type values must be agent filename stems (Bug S3-122)."""

    def test_invoke_agent_action_block_agent_types_match_agent_filenames(self):
        """Every literal `agent_type=...` argument paired with `action_type='invoke_agent'`
        in routing.py refers to a deployed agent filename stem.

        This is the action-block-side lock. We parse routing.py source,
        extract every `_make_action_block(action_type='invoke_agent', ..., agent_type='X', ...)`
        literal, and assert that 'X' is in the set of deployed agent stems.
        Catches the case where a routing branch references an agent_type that
        doesn't have a corresponding deployed agent file (the orchestrator
        would crash with `Unknown agent type` at spawn time).
        """
        import routing

        agents_dir = _resolve_agents_dir()
        existing_stems = {p.stem for p in agents_dir.glob("*.md")}
        routing_src = Path(routing.__file__).read_text()

        # Find every invoke_agent block and pull out the agent_type literal.
        # Pattern: action_type="invoke_agent" followed (within ~6 lines) by
        # agent_type="<identifier>". We use a multi-line regex over the source.
        invoke_blocks = re.finditer(
            r'action_type\s*=\s*"invoke_agent"\s*,\s*\n'
            r'(?:[^\n]*\n){0,10}?'
            r'\s*agent_type\s*=\s*"([a-z_][a-z0-9_]*)"',
            routing_src,
        )
        agent_types_used = {m.group(1) for m in invoke_blocks}

        # Some invoke_agent blocks may use a variable instead of a literal
        # (e.g., agent_type=PHASE_TO_AGENT[...]). Those are covered by the
        # PHASE_TO_AGENT test above, so we focus on literals here.
        # Skip the special "pass2_nested" sentinel which is a routing-internal
        # marker, not a real agent.
        agent_types_used.discard("pass2_nested")

        # Assertion: every literal agent_type in routing.py refers to an
        # existing deployed agent file.
        offenders = sorted(agent_types_used - existing_stems)
        assert not offenders, (
            "invoke_agent action blocks reference agent_type values that do "
            "not match any deployed agent filename (Bug S3-122 chain-lock). "
            f"Existing agent stems: {sorted(existing_stems)}. "
            f"Offenders: {offenders}"
        )

        # Sanity check: the parser actually found something (catches the case
        # where the regex breaks silently after a refactor).
        assert agent_types_used, (
            "No invoke_agent blocks with literal agent_type were found in "
            "routing.py. The regex parser may need to be updated for a "
            "refactored routing.py."
        )
