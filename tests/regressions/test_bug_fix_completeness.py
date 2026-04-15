"""
Structural completion audit for bug fixes (Bug S3-46, S3-80, S3-129).

Validates that all bug fix artifacts are consistent across workspace
and all delivered repositories. Run after every bug fix.

Bug S3-80: Also validates that deployed plugin artifacts (svp/commands/,
svp/agents/, svp/skills/, svp/hooks/) match their source Unit definitions.

Bug S3-129: Adds a round-trip regeneration test that uses
`regenerate_deployed_artifacts()` as its own oracle — copying the
delivered repo to a temp directory, running the function on the copy,
and asserting byte-for-byte and mode-bit parity between the copy and
the original. Closes three S3-80 coverage gaps: hook shell script
content, hook executable bits, and agent frontmatter drift on fields
other than `name`. Pattern P32 (Round-Trip Regeneration As Test Oracle).
"""
import re
import shutil
import sys
from pathlib import Path

import pytest

# pytestmark removed after comprehensive resync (2026-04-01)

# Paths relative to workspace root
WORKSPACE = Path(__file__).parent.parent.parent
PASS2_REPO = WORKSPACE.parent / "svp2.2-pass2-repo"


def _ws_spec() -> str:
    """Read spec from workspace (specs/) or consolidated repo (docs/)."""
    for p in (WORKSPACE / "specs" / "stakeholder_spec.md",
              WORKSPACE / "docs" / "stakeholder_spec.md"):
        if p.exists():
            return p.read_text()
    raise FileNotFoundError("stakeholder_spec.md not found in workspace")


def _ws_blueprint() -> str:
    """Read blueprint from workspace (blueprint/) or consolidated repo (docs/)."""
    for p in (WORKSPACE / "blueprint" / "blueprint_contracts.md",
              WORKSPACE / "docs" / "blueprint_contracts.md"):
        if p.exists():
            return p.read_text()
    raise FileNotFoundError("blueprint_contracts.md not found in workspace")


def _ws_lessons() -> str:
    """Read lessons learned from workspace (references/) or consolidated repo (docs/references/)."""
    for p in (WORKSPACE / "references" / "svp_2_1_lessons_learned.md",
              WORKSPACE / "docs" / "references" / "svp_2_1_lessons_learned.md"):
        if p.exists():
            return p.read_text()
    raise FileNotFoundError("svp_2_1_lessons_learned.md not found in workspace")


class TestSpecSync:
    """Spec must be identical in workspace and the delivered repo."""

    def test_spec_matches_pass2_repo(self):
        ws = _ws_spec()
        p2 = PASS2_REPO / "docs" / "stakeholder_spec.md"
        if p2.exists():
            assert ws == p2.read_text(), "Spec out of sync with Pass 2 repo"


class TestBlueprintSync:
    """Blueprint must be identical in workspace and the delivered repo."""

    def test_blueprint_matches_pass2_repo(self):
        ws = _ws_blueprint()
        p2 = PASS2_REPO / "docs" / "blueprint_contracts.md"
        if p2.exists():
            assert ws == p2.read_text(), "Blueprint out of sync with Pass 2 repo"


class TestLessonsLearnedSync:
    """Lessons learned must be identical in workspace and the delivered repo."""

    def test_lessons_learned_matches_pass2_repo(self):
        ws = _ws_lessons()
        p2 = PASS2_REPO / "docs" / "references" / "svp_2_1_lessons_learned.md"
        if p2.exists():
            assert ws == p2.read_text(), "Lessons learned out of sync with Pass 2 repo"


class TestDeliveryArtifactParity:
    """S3-50: Pass 2 repo must have all expected root-level delivery artifacts.

    Originally a parity check against Pass 1 repo. After Pass 1 retirement
    (2026-04-13) the test asserts against a canonical hardcoded list instead.
    """

    def test_pass2_repo_has_all_root_delivery_files(self):
        delivery_files = ["environment.yml", "pyproject.toml", "README.md",
                          "CHANGELOG.md", "LICENSE", ".gitignore"]
        for f in delivery_files:
            assert (PASS2_REPO / f).exists(), f"Pass 2 repo missing {f}"


class TestBugMarkerCompleteness:
    """Every bug referenced in spec must have a lessons learned entry."""

    def test_all_spec_bugs_in_lessons_learned(self):
        spec = _ws_spec()
        lessons = _ws_lessons()
        # Find S3-N markers (the bug catalog format used in this build)
        spec_bugs = set(re.findall(r"S3-\d+", spec))
        lessons_bugs = set(re.findall(r"S3-\d+", lessons))
        missing = spec_bugs - lessons_bugs
        # Filter: only bugs that appear as "Bug S3-N" in spec (not just passing references)
        spec_bug_entries = set(re.findall(r"Bug S3-\d+", spec))
        spec_bug_numbers = {m.replace("Bug ", "") for m in spec_bug_entries}
        missing_entries = spec_bug_numbers - lessons_bugs
        assert not missing_entries, (
            f"Bugs in spec but not in lessons learned: {sorted(missing_entries)}"
        )

    def test_all_regression_test_bugs_in_lessons_learned(self):
        """Every bug with a regression test file should have a lessons learned entry."""
        lessons = _ws_lessons()
        lessons_bugs = set(re.findall(r"S3-\d+", lessons))
        reg_dir = WORKSPACE / "tests" / "regressions"
        for f in reg_dir.glob("test_bug_s3_*.py"):
            # Extract bug numbers from filename
            file_bugs = set(re.findall(r"s3_(\d+)", f.name))
            for num in file_bugs:
                marker = f"S3-{num}"
                assert marker in lessons_bugs, (
                    f"Regression test {f.name} references {marker} but no lessons learned entry"
                )


# ---------------------------------------------------------------------------
# Bug S3-80: Deployed artifact freshness
# ---------------------------------------------------------------------------


class TestDeployedArtifactFreshness:
    """Deployed plugin artifacts must match their source Unit definitions.

    Bug S3-80: Claude Code loads deployed .md files from svp/commands/,
    svp/agents/, svp/skills/, and svp/hooks/ — not the Python source.
    These tests ensure the deployed files are never stale.
    """

    # --- Command definitions (Unit 25 → svp/commands/) ---

    def test_commands_match_source_pass2(self):
        """Every command .md in Pass 2 repo must match COMMAND_DEFINITIONS."""
        from slash_commands import COMMAND_DEFINITIONS

        commands_dir = PASS2_REPO / "svp" / "commands"
        if not commands_dir.is_dir():
            pytest.skip("Pass 2 repo has no svp/commands/")
        for cmd_name, source_content in COMMAND_DEFINITIONS.items():
            deployed = commands_dir / f"{cmd_name}.md"
            assert deployed.is_file(), f"Missing deployed command: {cmd_name}.md"
            assert deployed.read_text() == source_content, (
                f"Deployed {cmd_name}.md does not match source COMMAND_DEFINITIONS"
            )

    # --- Orchestration skill (Unit 26 → svp/skills/) ---

    def test_skill_matches_source_pass2(self):
        """SKILL.md in Pass 2 repo must match ORCHESTRATION_SKILL."""
        from orchestration_skill import ORCHESTRATION_SKILL

        skill_file = PASS2_REPO / "svp" / "skills" / "orchestration" / "SKILL.md"
        if not skill_file.is_file():
            pytest.skip("Pass 2 repo has no svp/skills/orchestration/SKILL.md")
        assert skill_file.read_text() == ORCHESTRATION_SKILL, (
            "Deployed SKILL.md does not match source ORCHESTRATION_SKILL"
        )

    # --- Agent definitions (Units 18-24 → svp/agents/) ---

    def _get_agent_defs(self):
        """Return the source agent definitions dict (filename -> content)."""
        from setup_agent import SETUP_AGENT_DEFINITION
        from blueprint_checker import BLUEPRINT_CHECKER_DEFINITION
        from construction_agents import (
            BLUEPRINT_AUTHOR_DEFINITION,
            BLUEPRINT_REVIEWER_DEFINITION,
            COVERAGE_REVIEW_AGENT_DEFINITION,
            IMPLEMENTATION_AGENT_DEFINITION,
            INTEGRATION_TEST_AUTHOR_DEFINITION,
            STAKEHOLDER_DIALOG_DEFINITION,
            STAKEHOLDER_REVIEWER_DEFINITION,
            TEST_AGENT_DEFINITION,
        )
        from diagnostic_agents import DIAGNOSTIC_AGENT_DEFINITION, REDO_AGENT_DEFINITION
        from support_agents import (
            HELP_AGENT_DEFINITION,
            HINT_AGENT_DEFINITION,
            REFERENCE_INDEXING_AGENT_DEFINITION,
        )
        from generate_assembly_map import (
            GIT_REPO_AGENT_DEFINITION,
            CHECKLIST_GENERATION_AGENT_DEFINITION,
            REGRESSION_ADAPTATION_AGENT_DEFINITION,
            ORACLE_AGENT_DEFINITION,
        )
        from debug_agents import BUG_TRIAGE_AGENT_DEFINITION, REPAIR_AGENT_DEFINITION

        return {
            "setup_agent.md": SETUP_AGENT_DEFINITION,
            "blueprint_checker.md": BLUEPRINT_CHECKER_DEFINITION,
            "stakeholder_dialog.md": STAKEHOLDER_DIALOG_DEFINITION,
            "stakeholder_reviewer.md": STAKEHOLDER_REVIEWER_DEFINITION,
            "blueprint_author.md": BLUEPRINT_AUTHOR_DEFINITION,
            "blueprint_reviewer.md": BLUEPRINT_REVIEWER_DEFINITION,
            "test_agent.md": TEST_AGENT_DEFINITION,
            "implementation_agent.md": IMPLEMENTATION_AGENT_DEFINITION,
            "coverage_review_agent.md": COVERAGE_REVIEW_AGENT_DEFINITION,
            "integration_test_author.md": INTEGRATION_TEST_AUTHOR_DEFINITION,
            "diagnostic_agent.md": DIAGNOSTIC_AGENT_DEFINITION,
            "redo_agent.md": REDO_AGENT_DEFINITION,
            "help_agent.md": HELP_AGENT_DEFINITION,
            "hint_agent.md": HINT_AGENT_DEFINITION,
            "reference_indexing.md": REFERENCE_INDEXING_AGENT_DEFINITION,
            "git_repo_agent.md": GIT_REPO_AGENT_DEFINITION,
            "checklist_generation.md": CHECKLIST_GENERATION_AGENT_DEFINITION,
            "regression_adaptation.md": REGRESSION_ADAPTATION_AGENT_DEFINITION,
            "oracle_agent.md": ORACLE_AGENT_DEFINITION,
            "bug_triage_agent.md": BUG_TRIAGE_AGENT_DEFINITION,
            "repair_agent.md": REPAIR_AGENT_DEFINITION,
        }

    def test_agents_match_source_pass2(self):
        """Every agent .md body in Pass 2 repo must match source definition."""
        agents_dir = PASS2_REPO / "svp" / "agents"
        if not agents_dir.is_dir():
            pytest.skip("Pass 2 repo has no svp/agents/")
        for filename, source_content in self._get_agent_defs().items():
            deployed = agents_dir / filename
            assert deployed.is_file(), f"Missing deployed agent: {filename}"
            deployed_text = deployed.read_text()
            # Agent files have YAML frontmatter prepended; check body after frontmatter
            assert source_content in deployed_text, (
                f"Deployed {filename} body does not match source definition"
            )

    # --- Hooks (Unit 17 → svp/hooks/) ---

    def test_hooks_json_matches_source_pass2(self):
        """hooks.json in Pass 2 repo must match generate_hooks_json()."""
        from hooks import generate_hooks_json

        hooks_file = PASS2_REPO / "svp" / "hooks" / "hooks.json"
        if not hooks_file.is_file():
            pytest.skip("Pass 2 repo has no svp/hooks/hooks.json")
        expected = generate_hooks_json() + "\n"
        assert hooks_file.read_text() == expected, (
            "Deployed hooks.json does not match source generate_hooks_json()"
        )

    # --- Round-trip regeneration (Bug S3-129) ---

    def test_no_drift_via_roundtrip_regeneration(self, tmp_path):
        """Copy PASS2_REPO, run regenerate_deployed_artifacts on the copy,
        assert byte-equal content and matching mode bits for every file.

        Bug S3-129: this uses the production function as its own oracle,
        closing three S3-80 coverage gaps at once — hook shell script
        content (write_authorization.sh, non_svp_protection.sh,
        stub_sentinel_check.sh, monitoring_reminder.sh), hook executable
        bits (chmod 0o755), and agent frontmatter drift on `description`
        and `model` fields. Pattern P32.
        """
        if not PASS2_REPO.is_dir():
            pytest.skip("Pass 2 repo not available")
        source_svp = PASS2_REPO / "svp"
        if not source_svp.is_dir():
            pytest.skip("Pass 2 repo has no svp/ plugin tree")

        from generate_assembly_map import regenerate_deployed_artifacts

        target = tmp_path / "repo_copy"
        shutil.copytree(PASS2_REPO, target, symlinks=False)
        regenerate_deployed_artifacts(target)

        target_svp = target / "svp"

        def _enum(root: Path) -> dict:
            """Enumerate regular files under root/{commands,agents,hooks,skills}
            keyed by relative path, skipping .DS_Store and __pycache__."""
            out = {}
            for category in ("commands", "agents", "hooks", "skills"):
                cat_dir = root / category
                if not cat_dir.is_dir():
                    continue
                for p in cat_dir.rglob("*"):
                    if not p.is_file():
                        continue
                    name = p.name
                    if name == ".DS_Store" or "__pycache__" in str(p):
                        continue
                    out[p.relative_to(root)] = p
            return out

        source_files = _enum(source_svp)
        target_files = _enum(target_svp)

        missing_in_target = sorted(set(source_files) - set(target_files))
        missing_in_source = sorted(set(target_files) - set(source_files))
        assert not missing_in_target, (
            "Round-trip regeneration did not reproduce these source files "
            f"(source has them, regenerated copy lost them): {missing_in_target}"
        )
        assert not missing_in_source, (
            "Round-trip regeneration produced files absent from source "
            f"(source never had them): {missing_in_source}. This usually "
            "means the source repo is missing an artifact that "
            "regenerate_deployed_artifacts would write — run "
            "`bash sync_workspace.sh` and recommit."
        )

        content_drift = []
        mode_drift = []
        for rel, sp in sorted(source_files.items()):
            tp = target_files[rel]
            if sp.read_bytes() != tp.read_bytes():
                content_drift.append(str(rel))
            if sys.platform != "win32":
                smode = sp.stat().st_mode & 0o777
                tmode = tp.stat().st_mode & 0o777
                if smode != tmode:
                    mode_drift.append(
                        f"{rel}: source={oct(smode)}, regenerated={oct(tmode)}"
                    )

        assert not content_drift, (
            "Deployed artifact content drift detected — the following files "
            "differ from what regenerate_deployed_artifacts would produce "
            "right now. Run `bash sync_workspace.sh` from the workspace to "
            "refresh the delivered repo. Files:\n  - "
            + "\n  - ".join(content_drift)
        )
        assert not mode_drift, (
            "Deployed artifact mode drift detected — the following files have "
            "different Unix permission bits than regenerate_deployed_artifacts "
            "would set. Most commonly this means a hook shell script lost its "
            "executable bit (0o755). Files:\n  - "
            + "\n  - ".join(mode_drift)
        )

