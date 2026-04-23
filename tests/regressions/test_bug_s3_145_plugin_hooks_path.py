"""Tests for Bug S3-145: svp_launcher deploys hooks from plugin_root/hooks/.

Real Claude Code plugin cache layout places hook scripts at
`plugin_root/hooks/`, not `plugin_root/svp/hooks/`. This test asserts:

1. The S3-108 regression fixture places hooks at the real path
   (`plugin_root/hooks/`, not `plugin_root/svp/hooks/`). Pins the
   correction against future drift that might reintroduce the
   mirror-the-bug fixture pattern.
2. create_new_project deploys hooks from `plugin_root/hooks/` to the
   project's `.claude/scripts/`.
"""

import inspect
from pathlib import Path

from svp_launcher import create_new_project

from tests.regressions import test_bug_s3_108_hook_deployment as s3_108_module


HOOK_SCRIPTS = ["write_authorization.sh", "non_svp_protection.sh"]


def test_s3_108_fixture_uses_plugin_root_hooks_not_svp_hooks():
    """_setup_plugin_with_hooks must create hooks at plugin_root/hooks/.

    Prior to S3-145, the fixture created hooks at plugin_root/svp/hooks/,
    which mirrored the buggy code path and silently validated wrong
    behavior. Inspect the fixture source to confirm the corrected path.
    """
    source = inspect.getsource(s3_108_module._setup_plugin_with_hooks)
    assert 'plugin_root / "hooks"' in source, (
        "Fixture should create hooks at plugin_root/hooks/ (post-S3-145). "
        f"Source:\n{source}"
    )
    # Also confirm the old path is no longer present as the hook-scripts
    # creation site (the comment may still mention it for history).
    assert '(plugin_root / "svp" / "hooks").mkdir' not in source, (
        "Fixture must no longer mkdir plugin_root/svp/hooks/"
    )


def test_create_new_project_deploys_from_plugin_root_hooks(tmp_path, monkeypatch):
    """End-to-end: hooks at plugin_root/hooks/ are deployed to .claude/scripts/."""
    import json

    # create_new_project builds at Path.cwd() / name — chdir into tmp_path so
    # the created project is auto-cleaned by pytest.
    monkeypatch.chdir(tmp_path)

    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()

    # Minimal plugin scaffolding
    scripts_dir = plugin_root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "routing.py").write_text("# routing\n")

    toolchain_dir = plugin_root / "toolchains"
    toolchain_dir.mkdir()
    (toolchain_dir / "python_conda_pytest.json").write_text("{}\n")

    ruff_file = plugin_root / "ruff.toml"
    ruff_file.write_text("line-length = 88\n")

    plugin_json_dir = plugin_root / ".claude-plugin"
    plugin_json_dir.mkdir()
    (plugin_json_dir / "plugin.json").write_text(
        json.dumps({"name": "svp", "version": "2.2.0"})
    )

    # Hooks at the REAL path: plugin_root/hooks/
    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir()
    for name in HOOK_SCRIPTS:
        (hooks_dir / name).write_text(f"#!/usr/bin/env bash\n# {name}\n")
        (hooks_dir / name).chmod(0o755)

    project_root = create_new_project("s3_145_hooks", plugin_root)

    deployed = project_root / ".claude" / "scripts"
    assert deployed.is_dir(), "Project must have .claude/scripts/ after create"
    for name in HOOK_SCRIPTS:
        deployed_script = deployed / name
        assert deployed_script.is_file(), (
            f"{name} must be deployed from plugin_root/hooks/ to "
            "project/.claude/scripts/"
        )
