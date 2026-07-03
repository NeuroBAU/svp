"""Regression tests for Bug S3-210: macOS framework-Python install path.

The delivered README's macOS/Linux launcher-install instruction
(`pip install -e . --prefix ~/.local`) placed the package off ``sys.path`` on
macOS *framework* Python builds (python.org / MacPorts), whose only scanned user
site is ``~/Library/Python/X.Y/lib/python/site-packages``. The console script
ran but ``import svp`` raised ``ModuleNotFoundError``. Related friction: MacPorts
ships pip separately, and the launcher's (intended) pytest preflight had no
installable extra.

Fixes (all repo-native delivery artifacts):
  1. README recommends ``pip install -e . --user`` + documents the macOS /
     MacPorts caveat.
  2. ``pyproject.toml`` declares a ``test`` optional-dependency extra so
     ``pip install -e '.[test]'`` pulls pytest into the same interpreter.
  3. ``setup_svp_user.sh`` -- POSIX no-pip activator (sibling of the Windows
     ``setup_svp_user.ps1``) that adds a ``svp`` shell function invoking the
     launcher directly.

These assert on the *delivered repo* (resolved dynamically), skipping cleanly
where it is not present so the suite stays portable across machines.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest


def _pass2_repo() -> Path:
    """Resolve the delivered Pass 2 repo, or skip if it isn't available.

    Resolution order: ``SVP_PASS2_REPO`` env var, then the conventional sibling
    ``<repo-parent>/svp2.2-pass2-repo``. Mirrors the resolver in
    ``test_bug_s3_43_restore_references.py`` so these tests remain meaningful
    where the repo exists and skip cleanly where it does not.
    """
    env = os.environ.get("SVP_PASS2_REPO")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.append(Path(__file__).resolve().parents[2].parent / "svp2.2-pass2-repo")
    for repo in candidates:
        if repo.is_dir():
            return repo
    pytest.skip("Pass 2 delivered repo not present (set SVP_PASS2_REPO to enable)")


# ---------------------------------------------------------------------------
# (a) pyproject.toml declares a `test` extra containing pytest
# ---------------------------------------------------------------------------
def test_pyproject_declares_test_extra_with_pytest():
    """S3-210: `pip install -e '.[test]'` must pull pytest for the preflight."""
    repo = _pass2_repo()
    pyproject = repo / "pyproject.toml"
    assert pyproject.is_file(), "delivered repo missing pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    extras = data.get("project", {}).get("optional-dependencies", {})
    assert "test" in extras, "pyproject.toml [project.optional-dependencies] missing 'test' extra"
    joined = " ".join(extras["test"]).lower()
    assert "pytest" in joined, f"'test' extra must include pytest, got {extras['test']!r}"


# ---------------------------------------------------------------------------
# (b) setup_svp_user.sh exists, is executable, and is correctly shaped
# ---------------------------------------------------------------------------
def test_setup_svp_user_sh_exists_and_executable():
    """S3-210: the POSIX no-pip activator ships and is runnable."""
    repo = _pass2_repo()
    sh = repo / "setup_svp_user.sh"
    assert sh.is_file(), "delivered repo missing setup_svp_user.sh"
    assert os.access(sh, os.X_OK), "setup_svp_user.sh must be executable (chmod +x)"


def test_setup_svp_user_sh_defines_svp_function_and_plugin_root():
    """S3-210: the activator must export SVP_PLUGIN_ROOT and define a `svp`
    shell function that invokes the launcher directly (no pip, relocation-safe)."""
    repo = _pass2_repo()
    body = (repo / "setup_svp_user.sh").read_text(encoding="utf-8")
    assert "SVP_PLUGIN_ROOT" in body, "must export SVP_PLUGIN_ROOT"
    assert "svp() {" in body, "must define a `svp` shell function"
    assert "svp_launcher.py" in body, "the `svp` function must invoke svp_launcher.py directly"


# ---------------------------------------------------------------------------
# (c) README recommends --user and documents the macOS / MacPorts caveat
# ---------------------------------------------------------------------------
def test_readme_recommends_user_install_and_documents_macos_caveat():
    """S3-210: README must recommend `pip install -e . --user` and warn about
    macOS framework Python / MacPorts (not the old `--prefix ~/.local`)."""
    repo = _pass2_repo()
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert "pip install -e . --user" in readme, "README must recommend `pip install -e . --user`"
    lower = readme.lower()
    assert "framework" in lower and "macports" in lower, (
        "README must document the macOS framework-Python / MacPorts caveat"
    )
    assert "setup_svp_user.sh" in readme, "README must reference the setup_svp_user.sh fallback"
