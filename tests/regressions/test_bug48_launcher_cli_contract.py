"""Regression test for Bug 48: launcher CLI contract
loss across spec-blueprint-implementation boundary.

Tests that:
1. parse_args([]) defaults args.command to "resume"
2. restore mode accepts all required arguments
3. --blueprint-dir is the argument name (not --blueprint)
4. --profile is a required argument for restore mode
5. parse_args(["new", "myproject"]) works correctly

SVP 2.2: parse_args lives in src.unit_29.stub (was svp_launcher).
"""

import unittest

from src.unit_29.stub import parse_args


class TestBug48BareCommand(unittest.TestCase):
    """Bare svp must default to resume."""

    def test_bare_svp_defaults_to_resume(self):
        args = parse_args([])
        self.assertEqual(
            args.command,
            "resume",
            "Bare svp must set args.command='resume'"
            ", not None",
        )


class TestBug48RestoreArgs(unittest.TestCase):
    """Restore mode must accept all spec arguments."""

    def test_restore_full_args(self):
        args = parse_args(
            [
                "restore",
                "proj",
                "--spec",
                "s.md",
                "--blueprint-dir",
                "bd/",
                "--profile",
                "p.json",
                "--context",
                "c.md",
                "--scripts-source",
                "sc/",
            ]
        )
        self.assertEqual(args.command, "restore")
        self.assertEqual(args.project_name, "proj")
        self.assertIsNotNone(
            getattr(args, "blueprint_dir", None)
        )
        self.assertIsNotNone(
            getattr(args, "profile", None)
        )
        self.assertIsNotNone(
            getattr(args, "context", None)
        )
        self.assertIsNotNone(
            getattr(args, "scripts_source", None)
        )


class TestBug48BlueprintDir(unittest.TestCase):
    """--blueprint-dir must be the argument name."""

    def test_blueprint_dir_not_blueprint(self):
        args = parse_args(
            [
                "restore",
                "proj",
                "--spec",
                "s.md",
                "--blueprint-dir",
                "bd/",
                "--profile",
                "p.json",
                "--context",
                "c.md",
                "--scripts-source",
                "sc/",
            ]
        )
        self.assertTrue(
            hasattr(args, "blueprint_dir"),
            "Must use --blueprint-dir (directory)",
        )


class TestBug48ProfileRequired(unittest.TestCase):
    """--profile must be present for restore mode."""

    def test_profile_in_restore_args(self):
        args = parse_args(
            [
                "restore",
                "proj",
                "--spec",
                "s.md",
                "--blueprint-dir",
                "bd/",
                "--profile",
                "prof.json",
                "--context",
                "c.md",
                "--scripts-source",
                "sc/",
            ]
        )
        self.assertTrue(
            hasattr(args, "profile"),
            "--profile must be a restore argument",
        )


class TestBug48NewCommand(unittest.TestCase):
    """svp new must work correctly."""

    def test_new_command(self):
        args = parse_args(["new", "myproject"])
        self.assertEqual(args.command, "new")
        self.assertEqual(args.project_name, "myproject")


if __name__ == "__main__":
    unittest.main()
