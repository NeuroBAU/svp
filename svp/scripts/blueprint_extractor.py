"""Blueprint Extractor -- Unit 5 of the SVP pipeline.

Extracts a single unit's definition and upstream contract signatures from
the full blueprint for context-isolated agent invocations. The extracted
content becomes part of the task prompt for the relevant subagent. This is
a deterministic operation -- no LLM involvement. Implements spec Section 10.11.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import re


class UnitDefinition:
    """A single unit's complete definition extracted from the blueprint."""
    unit_number: int
    unit_name: str
    description: str          # Tier 1
    signatures: str           # Tier 2 code block (raw Python)
    invariants: str           # Tier 2 invariants code block
    error_conditions: str     # Tier 3
    behavioral_contracts: str # Tier 3
    dependencies: List[int]   # upstream unit numbers

    def __init__(self, **kwargs: Any) -> None:
        self.unit_number = kwargs["unit_number"]
        self.unit_name = kwargs["unit_name"]
        self.description = kwargs.get("description", "")
        self.signatures = kwargs.get("signatures", "")
        self.invariants = kwargs.get("invariants", "")
        self.error_conditions = kwargs.get("error_conditions", "")
        self.behavioral_contracts = kwargs.get("behavioral_contracts", "")
        self.dependencies = kwargs.get("dependencies", [])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Pattern that matches unit heading lines: ## Unit N: Name
_UNIT_HEADING_RE = re.compile(r"^##\s+Unit\s+(\d+):\s+(.+)$", re.MULTILINE)

# Dash pattern: matches em-dash, en-dash, or one-or-more hyphens
# Used in section heading patterns like "### Tier 1 -- Description"
# or "### Tier 2 \u2014 Signatures"
_DASH_PATTERN = r"(?:\u2014|\u2013|-+)"


def _read_blueprint(blueprint_path: Path) -> str:
    """Read blueprint file, enforcing the existence pre-condition."""
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    return blueprint_path.read_text(encoding="utf-8")


def _find_unit_sections(text: str) -> List[Dict[str, Any]]:
    """Find all unit sections in the blueprint text.

    Returns a list of dicts: {unit_number, unit_name, raw} where raw is the
    full markdown text of the unit section (from heading to just before the
    next unit heading or end of text, with trailing '---' separators stripped).
    """
    matches = list(_UNIT_HEADING_RE.finditer(text))
    if not matches:
        return []

    sections: List[Dict[str, Any]] = []
    for i, m in enumerate(matches):
        start = m.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        raw_section = text[start:end]
        # Strip trailing whitespace and a trailing '---' separator if present
        stripped = raw_section.rstrip()
        if stripped.endswith("---"):
            stripped = stripped[:-3].rstrip()

        sections.append({
            "unit_number": int(m.group(1)),
            "unit_name": m.group(2).strip(),
            "raw": stripped,
        })
    return sections


def _extract_section_between_headings(
    unit_text: str,
    heading_pattern: str,
    stop_pattern: str = r"^###\s+",
) -> str:
    """Extract the text between a heading matching heading_pattern and
    the next ### heading (or end of text).

    Returns the text content (without the heading line itself), stripped.
    """
    heading_re = re.compile(heading_pattern, re.IGNORECASE | re.MULTILINE)
    heading_match = heading_re.search(unit_text)
    if heading_match is None:
        return ""

    # Find the end of the heading line
    remaining = unit_text[heading_match.end():]

    # Find the next ### heading
    next_heading = re.search(stop_pattern, remaining, re.MULTILINE)
    if next_heading:
        content = remaining[:next_heading.start()]
    else:
        content = remaining

    return content.strip()


def _extract_code_block(text: str, language: str = "python") -> str:
    """Extract the first fenced code block with the given language tag from text.

    Returns the content inside the fences, or empty string if not found.
    """
    pattern = re.compile(
        r"```" + re.escape(language) + r"\s*\n(.*?)```",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        return ""
    return match.group(1).rstrip("\n")


def _extract_signatures(unit_text: str) -> str:
    """Extract the Python code block from the Tier 2 -- Signatures section."""
    section = _extract_section_between_headings(
        unit_text,
        r"^###\s+Tier\s+2\s*" + _DASH_PATTERN + r"\s*Signatures",
    )
    if not section:
        return ""
    return _extract_code_block(section, "python")


def _extract_invariants(unit_text: str) -> str:
    """Extract the Python code block from the Tier 2 -- Invariants section."""
    section = _extract_section_between_headings(
        unit_text,
        r"^###\s+Tier\s+2\s*" + _DASH_PATTERN + r"\s*Invariants",
    )
    if not section:
        return ""
    return _extract_code_block(section, "python")


def _extract_description(unit_text: str) -> str:
    """Extract the Tier 1 -- Description section content."""
    return _extract_section_between_headings(
        unit_text,
        r"^###\s+Tier\s+1\s*" + _DASH_PATTERN + r"\s*Description",
    )


def _extract_error_conditions(unit_text: str) -> str:
    """Extract the Tier 3 -- Error Conditions section content."""
    return _extract_section_between_headings(
        unit_text,
        r"^###\s+Tier\s+3\s*" + _DASH_PATTERN + r"\s*Error\s+Conditions",
    )


def _extract_behavioral_contracts(unit_text: str) -> str:
    """Extract the Tier 3 -- Behavioral Contracts section content."""
    return _extract_section_between_headings(
        unit_text,
        r"^###\s+Tier\s+3\s*" + _DASH_PATTERN + r"\s*Behavioral\s+Contracts",
    )


def _parse_dependency_numbers(unit_text: str) -> List[int]:
    """Parse unit numbers from the Tier 3 -- Dependencies section.

    Looks for references to other units in the dependency section.
    Handles multiple formats:
      - **Unit N (Name):** ...
      - Unit N
      - unit N
    Also handles the case where the section says "None".
    """
    dep_section = _extract_section_between_headings(
        unit_text,
        r"^###\s+Tier\s+3\s*" + _DASH_PATTERN + r"\s*Dependencies",
    )
    if not dep_section:
        return []

    # Check for "None" (no dependencies)
    stripped = dep_section.strip()
    if not stripped:
        return []

    # If the section starts with "None" (possibly followed by period or
    # additional explanatory text), treat as no dependencies
    if re.match(r"^None\b", stripped, re.IGNORECASE):
        return []

    # Find all Unit N references (various formats)
    dep_unit_re = re.compile(r"[Uu]nit\s+(\d+)")
    return sorted(set(int(m.group(1)) for m in dep_unit_re.finditer(dep_section)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_blueprint(blueprint_path: Path) -> List[UnitDefinition]:
    """Read the full blueprint and parse all unit definitions into
    UnitDefinition instances. Splits on `## Unit N:` heading patterns.

    Args:
        blueprint_path: Path to the blueprint markdown file.

    Returns:
        A list of UnitDefinition instances, one per unit, ordered by
        appearance in the blueprint.

    Raises:
        FileNotFoundError: If the blueprint file does not exist.
        ValueError: If the blueprint contains no parseable unit definitions.
    """
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    text = _read_blueprint(blueprint_path)
    sections = _find_unit_sections(text)

    if not sections:
        raise ValueError("Blueprint has no parseable unit definitions")

    result: List[UnitDefinition] = []
    for section in sections:
        raw = section["raw"]
        unit_def = UnitDefinition(
            unit_number=section["unit_number"],
            unit_name=section["unit_name"],
            description=_extract_description(raw),
            signatures=_extract_signatures(raw),
            invariants=_extract_invariants(raw),
            error_conditions=_extract_error_conditions(raw),
            behavioral_contracts=_extract_behavioral_contracts(raw),
            dependencies=_parse_dependency_numbers(raw),
        )
        result.append(unit_def)

    # Post-conditions
    assert len(result) > 0, "Blueprint must contain at least one unit"
    assert all(u.unit_number > 0 for u in result), "All unit numbers must be positive"

    return result


def extract_unit(blueprint_path: Path, unit_number: int) -> UnitDefinition:
    """Return a single unit's definition. Delegates to parse_blueprint internally.

    Args:
        blueprint_path: Path to the blueprint markdown file.
        unit_number: The unit number to extract (must be >= 1).

    Returns:
        The UnitDefinition for the requested unit.

    Raises:
        FileNotFoundError: If the blueprint file does not exist.
        ValueError: If the unit is not found in the blueprint.
    """
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    assert unit_number >= 1, "Unit number must be positive"

    units = parse_blueprint(blueprint_path)

    for unit_def in units:
        if unit_def.unit_number == unit_number:
            # Post-conditions
            assert unit_def.unit_number == unit_number, "Extracted unit number must match request"
            assert len(unit_def.signatures) > 0, "Unit must have non-empty signatures"
            return unit_def

    raise ValueError(f"Unit {unit_number} not found in blueprint")


def extract_upstream_contracts(
    blueprint_path: Path, unit_number: int
) -> List[Dict[str, str]]:
    """Return the Tier 2 signatures for all units listed in the requested
    unit's dependencies.

    Each entry is a dict with `unit_number`, `unit_name`, and `signatures` keys.

    Args:
        blueprint_path: Path to the blueprint markdown file.
        unit_number: The unit whose dependencies to resolve.

    Returns:
        A list of dicts, one per upstream dependency, ordered by unit number.

    Raises:
        FileNotFoundError: If the blueprint file does not exist.
        ValueError: If the unit is not found in the blueprint.
    """
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    assert unit_number >= 1, "Unit number must be positive"

    units = parse_blueprint(blueprint_path)

    # Build a lookup from unit number to UnitDefinition
    unit_map: Dict[int, UnitDefinition] = {}
    for u in units:
        unit_map[u.unit_number] = u

    if unit_number not in unit_map:
        raise ValueError(f"Unit {unit_number} not found in blueprint")

    target = unit_map[unit_number]
    dep_numbers = target.dependencies

    upstream: List[Dict[str, str]] = []
    for dep_num in dep_numbers:
        if dep_num not in unit_map:
            # Dependency references a unit not in the blueprint; skip
            continue
        dep_unit = unit_map[dep_num]
        upstream.append({
            "unit_number": str(dep_unit.unit_number),
            "unit_name": dep_unit.unit_name,
            "signatures": dep_unit.signatures,
        })

    return upstream


def build_unit_context(
    blueprint_path: Path, unit_number: int
) -> str:
    """Produce a formatted string containing the unit's full definition
    followed by all upstream contract signatures, ready for inclusion
    in a task prompt.

    Args:
        blueprint_path: Path to the blueprint markdown file.
        unit_number: The unit to build context for.

    Returns:
        A formatted string with the unit definition and upstream contracts.

    Raises:
        FileNotFoundError: If the blueprint file does not exist.
        ValueError: If the unit is not found in the blueprint.
    """
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    assert unit_number >= 1, "Unit number must be positive"

    unit_def = extract_unit(blueprint_path, unit_number)
    upstream = extract_upstream_contracts(blueprint_path, unit_number)

    # Build the context string
    parts: List[str] = []

    # Unit definition section
    parts.append(f"## Unit {unit_def.unit_number}: {unit_def.unit_name}")
    parts.append("")

    if unit_def.description:
        parts.append("### Tier 1 -- Description")
        parts.append("")
        parts.append(unit_def.description)
        parts.append("")

    if unit_def.signatures:
        parts.append("### Tier 2 \u2014 Signatures")
        parts.append("")
        parts.append("```python")
        parts.append(unit_def.signatures)
        parts.append("```")
        parts.append("")

    if unit_def.invariants:
        parts.append("### Tier 2 \u2014 Invariants")
        parts.append("")
        parts.append("```python")
        parts.append(unit_def.invariants)
        parts.append("```")
        parts.append("")

    if unit_def.error_conditions:
        parts.append("### Tier 3 -- Error Conditions")
        parts.append("")
        parts.append(unit_def.error_conditions)
        parts.append("")

    if unit_def.behavioral_contracts:
        parts.append("### Tier 3 -- Behavioral Contracts")
        parts.append("")
        parts.append(unit_def.behavioral_contracts)
        parts.append("")

    # Upstream contracts section
    if upstream:
        parts.append("## Upstream Contract Signatures")
        parts.append("")
        for contract in upstream:
            parts.append(f"### Unit {contract['unit_number']}: {contract['unit_name']}")
            parts.append("")
            if contract["signatures"]:
                parts.append("```python")
                parts.append(contract["signatures"])
                parts.append("```")
                parts.append("")

    result = "\n".join(parts)

    # Post-condition
    assert len(result) > 0, "Unit context must be non-empty"

    return result
