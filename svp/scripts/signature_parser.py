"""Unit 9: Signature Parser Dispatch.

Provides a dispatch table of language-specific signature parsers and a CLI
entry point for extracting signatures from blueprint Tier 2 code blocks.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

# ---------------------------------------------------------------------------
# Language-specific parsers
# ---------------------------------------------------------------------------


def _parse_python_signatures(source: str, language_config: Dict[str, Any]) -> Any:
    """Parse Python source using ast.parse(). Returns ast.Module.

    Raises SyntaxError on invalid Python.
    """
    return ast.parse(source)


def _parse_r_signatures(
    source: str, language_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Regex-based parser for R function assignments.

    Finds patterns like: name <- function(args) { ... }
    Returns a list of dicts with function definition info.
    """
    results: List[Dict[str, Any]] = []

    # Match R function assignments: name <- function(args)
    # Also handle name = function(args) as valid R assignment
    pattern = re.compile(
        r"^(\w+)\s*(?:<-|=)\s*function\s*\(([^)]*)\)",
        re.MULTILINE,
    )

    for m in pattern.finditer(source):
        func_name = m.group(1)
        args_str = m.group(2).strip()

        # Parse arguments
        args: List[str] = []
        if args_str:
            for arg in args_str.split(","):
                arg = arg.strip()
                if arg:
                    # Strip default values for the argument name
                    arg_name = arg.split("=")[0].strip()
                    args.append(arg_name)

        results.append(
            {
                "name": func_name,
                "args": args,
                "raw_args": args_str,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

SIGNATURE_PARSERS: Dict[str, Callable[[str, Dict[str, Any]], Any]] = {
    "python": _parse_python_signatures,
    "r": _parse_r_signatures,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_signatures(
    source: str,
    language: str,
    language_config: Dict[str, Any],
) -> Any:
    """Look up and dispatch to the language-specific signature parser.

    Raises KeyError if no parser is registered for the given language.
    Component languages (e.g., Stan) and plugin artifact types do not have
    entries in SIGNATURE_PARSERS -- they bypass parsing entirely (handled
    by Unit 10).
    """
    if language not in SIGNATURE_PARSERS:
        raise KeyError(f"No signature parser for language: {language}")
    parser = SIGNATURE_PARSERS[language]
    return parser(source, language_config)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list = None) -> None:
    """CLI entry point for signature parsing.

    Arguments:
        --blueprint: path to blueprint_contracts.md
        --unit: unit number (int)
        --language: language identifier (str)
    """
    parser = argparse.ArgumentParser(
        description="Parse signatures from a blueprint unit's Tier 2 block."
    )
    parser.add_argument(
        "--blueprint", type=str, required=True, help="Path to blueprint_contracts.md"
    )
    parser.add_argument(
        "--unit", type=int, required=True, help="Unit number to extract"
    )
    parser.add_argument(
        "--language", type=str, required=True, help="Language identifier"
    )

    args = parser.parse_args(argv)

    try:
        blueprint_path = Path(args.blueprint)
        text = blueprint_path.read_text(encoding="utf-8")

        # Extract the section for the requested unit
        tier2_source = _extract_unit_tier2(text, args.unit)

        if tier2_source is None:
            print(f"Error: Unit {args.unit} not found in blueprint", file=sys.stderr)
            sys.exit(1)

        # Get language config from registry
        from language_registry import get_language_config

        language_config = get_language_config(args.language)

        # Parse signatures
        result = parse_signatures(tier2_source, args.language, language_config)
        print(result)

    except SyntaxError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_UNIT_HEADING_RE = re.compile(r"^## Unit (\d+):\s*(.+?)\s*$", re.MULTILINE)
_TIER2_HEADING_RE = re.compile(r"^### Tier 2", re.MULTILINE)
_TIER3_HEADING_RE = re.compile(r"^### Tier 3", re.MULTILINE)


def _extract_unit_tier2(text: str, unit_number: int) -> str | None:
    """Extract and return the Tier 2 code block content for a given unit number.

    Returns None if the unit is not found.
    """
    # Find all unit headings
    matches = list(_UNIT_HEADING_RE.finditer(text))

    section_text = None
    for i, m in enumerate(matches):
        num = int(m.group(1))
        if num == unit_number:
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end]
            break

    if section_text is None:
        return None

    # Find Tier 2 heading
    t2_match = _TIER2_HEADING_RE.search(section_text)
    if not t2_match:
        return None

    # Find Tier 3 heading (end boundary for Tier 2)
    t3_match = _TIER3_HEADING_RE.search(section_text)

    if t3_match:
        t2_line_end = section_text.index("\n", t2_match.start()) + 1
        tier2_raw = section_text[t2_line_end : t3_match.start()]
    else:
        t2_line_end = section_text.index("\n", t2_match.start()) + 1
        tier2_raw = section_text[t2_line_end:]

    # Strip code fences
    return _strip_code_fences(tier2_raw).strip()


def _strip_code_fences(text: str) -> str:
    """Remove opening ```language and closing ``` lines from code blocks."""
    lines = text.split("\n")
    result = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if not in_fence and re.match(r"^```\w*\s*$", stripped):
            in_fence = True
            continue
        elif in_fence and stripped == "```":
            in_fence = False
            continue
        else:
            result.append(line)
    return "\n".join(result)
