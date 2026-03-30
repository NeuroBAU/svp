"""Unit 8: Blueprint Extractor.

Provides functions to parse the two blueprint files and extract unit definitions,
upstream contracts, and per-unit metadata.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from svp_config import ARTIFACT_FILENAMES


@dataclass
class UnitDefinition:
    number: int
    name: str
    tier1: str
    tier2: str
    tier3: str
    dependencies: List[int]
    languages: Set[str]
    machinery: (
        bool  # True for units whose contracts affect pipeline mechanisms (5, 6, 14, 15)
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Pattern matching "## Unit N: Name"
_UNIT_HEADING_RE = re.compile(r"^## Unit (\d+):\s*(.+?)\s*$", re.MULTILINE)

# Pattern matching Tier 2 subheading (prefix match accommodating em-dash/suffix)
_TIER2_HEADING_RE = re.compile(r"^### Tier 2", re.MULTILINE)

# Pattern matching Tier 3 subheading
_TIER3_HEADING_RE = re.compile(r"^### Tier 3", re.MULTILINE)

# Pattern for code fences: opening ```lang or just ```
_CODE_FENCE_OPEN_RE = re.compile(r"^```(\w+)?\s*$", re.MULTILINE)

# Pattern for Dependencies line in Tier 3
_DEPENDENCIES_RE = re.compile(r"\*\*Dependencies:\*\*\s*(.*?)$", re.MULTILINE)

# Resolve blueprint filenames from ARTIFACT_FILENAMES (no hardcoded paths)
_PROSE_FILENAME = Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
_CONTRACTS_FILENAME = Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name


def _extract_sections_by_unit_heading(text: str) -> Dict[int, tuple]:
    """Split text into per-unit sections keyed by unit number.

    Returns dict mapping unit_number -> (name, section_text).
    section_text is everything from the heading line to the next unit heading or EOF.
    """
    matches = list(_UNIT_HEADING_RE.finditer(text))
    sections: Dict[int, tuple] = {}
    for i, m in enumerate(matches):
        unit_num = int(m.group(1))
        name = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[unit_num] = (name, text[start:end])
    return sections


def _strip_code_fences(text: str) -> str:
    """Remove opening ```language and closing ``` lines from code blocks.

    Returns the content between fences, preserving everything else.
    """
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


def _parse_dependencies(tier3_text: str) -> List[int]:
    """Extract dependency unit numbers from the Dependencies: line in Tier 3."""
    m = _DEPENDENCIES_RE.search(tier3_text)
    if not m:
        return []
    deps_str = m.group(1).strip()
    if not deps_str or deps_str.lower().startswith("none"):
        return []
    # Parse "Unit 1, Unit 2, Unit 8" etc.
    unit_nums = re.findall(r"Unit\s+(\d+)", deps_str)
    return sorted(int(n) for n in unit_nums)


def _extract_tier2_tier3(section_text: str) -> tuple:
    """Extract Tier 2 and Tier 3 from a contracts file unit section.

    Returns (tier2_text, tier3_text).
    """
    # Find Tier 2 heading (prefix match)
    t2_match = _TIER2_HEADING_RE.search(section_text)
    # Find Tier 3 heading
    t3_match = _TIER3_HEADING_RE.search(section_text)

    tier2 = ""
    tier3 = ""

    if t2_match and t3_match:
        # Tier 2 is from after the Tier 2 heading line to the Tier 3 heading
        t2_line_end = section_text.index("\n", t2_match.start()) + 1
        tier2 = section_text[t2_line_end : t3_match.start()]
        # Tier 3 is from after the Tier 3 heading line to end of section
        t3_line_end = section_text.index("\n", t3_match.start()) + 1
        tier3 = section_text[t3_line_end:]
    elif t2_match and not t3_match:
        t2_line_end = section_text.index("\n", t2_match.start()) + 1
        tier2 = section_text[t2_line_end:]
    elif t3_match and not t2_match:
        t3_line_end = section_text.index("\n", t3_match.start()) + 1
        tier3 = section_text[t3_line_end:]

    return tier2.strip(), tier3.strip()


def _detect_languages_in_text(text: str) -> Set[str]:
    """Detect code fence language tags in text.

    Returns set of language strings. Untagged fences get mapped to project's
    primary language (python).
    """
    languages: Set[str] = set()
    # Known language mappings
    lang_map = {"python": "python", "r": "r", "stan": "stan"}

    for m in _CODE_FENCE_OPEN_RE.finditer(text):
        tag = m.group(1)
        if tag is None:
            # Untagged fence defaults to project's primary language
            languages.add("python")
        else:
            tag_lower = tag.lower()
            if tag_lower in lang_map:
                languages.add(lang_map[tag_lower])
            else:
                # Unknown tag - still record it
                languages.add(tag_lower)

    return languages


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_units(blueprint_dir: Path) -> List[UnitDefinition]:
    """Parse blueprint_prose.md and blueprint_contracts.md to extract all unit definitions.

    Returns list of UnitDefinition sorted by unit number.
    """
    prose_path = blueprint_dir / _PROSE_FILENAME
    contracts_path = blueprint_dir / _CONTRACTS_FILENAME

    prose_text = prose_path.read_text(encoding="utf-8")
    contracts_text = contracts_path.read_text(encoding="utf-8")

    # Extract per-unit sections from prose (Tier 1)
    prose_sections = _extract_sections_by_unit_heading(prose_text)

    # Extract per-unit sections from contracts (Tier 2 + Tier 3)
    contracts_sections = _extract_sections_by_unit_heading(contracts_text)

    # Get the union of all unit numbers
    all_unit_numbers = sorted(
        set(prose_sections.keys()) | set(contracts_sections.keys())
    )

    units: List[UnitDefinition] = []
    for unit_num in all_unit_numbers:
        # Get name from whichever source has it
        name = ""
        tier1 = ""
        tier2 = ""
        tier3 = ""

        if unit_num in prose_sections:
            name = prose_sections[unit_num][0]
            # Tier 1 is the full section text from prose
            tier1 = prose_sections[unit_num][1].strip()

        if unit_num in contracts_sections:
            if not name:
                name = contracts_sections[unit_num][0]
            section_text = contracts_sections[unit_num][1]
            raw_tier2, tier3 = _extract_tier2_tier3(section_text)
            # Strip code fence markers from Tier 2
            tier2 = _strip_code_fences(raw_tier2).strip()

        # Parse dependencies from Tier 3
        dependencies = _parse_dependencies(tier3)

        # Detect languages from both files for this unit
        languages = detect_code_block_language(blueprint_dir, unit_num)

        # Check machinery flag in Tier 1
        machinery = "machinery: true" in tier1.lower() if tier1 else False

        units.append(
            UnitDefinition(
                number=unit_num,
                name=name,
                tier1=tier1,
                tier2=tier2,
                tier3=tier3,
                dependencies=dependencies,
                languages=languages,
                machinery=machinery,
            )
        )

    return units


def build_unit_context(
    unit: UnitDefinition,
    all_units: List[UnitDefinition],
    include_tier1: bool = True,
) -> str:
    """Assemble context for a single unit.

    If include_tier1=True: includes unit's Tier 1, Tier 2, and Tier 3.
    If include_tier1=False: includes unit's Tier 2 and Tier 3 only.
    Appends upstream contracts: for each dependency, includes the dependency
    unit's Tier 2 and Tier 3 (never Tier 1 for upstream).
    """
    # Build lookup for all units by number
    unit_map: Dict[int, UnitDefinition] = {u.number: u for u in all_units}

    parts: List[str] = []

    # Include the target unit's tiers
    if include_tier1 and unit.tier1:
        parts.append(unit.tier1)
    if unit.tier2:
        parts.append(unit.tier2)
    if unit.tier3:
        parts.append(unit.tier3)

    # Include upstream dependencies' Tier 2 + Tier 3 (not Tier 1)
    for dep_num in unit.dependencies:
        dep_unit = unit_map.get(dep_num)
        if dep_unit is not None:
            if dep_unit.tier2:
                parts.append(dep_unit.tier2)
            if dep_unit.tier3:
                parts.append(dep_unit.tier3)

    return "\n\n".join(parts)


def detect_code_block_language(
    blueprint_dir: Path,
    unit_number: int,
) -> Set[str]:
    """Read code fence tags from BOTH blueprint files for a given unit.

    Returns set of detected languages. Mapping:
      python -> "python", r -> "r", stan -> "stan".
    Untagged code fences default to project's primary language.
    """
    prose_path = blueprint_dir / _PROSE_FILENAME
    contracts_path = blueprint_dir / _CONTRACTS_FILENAME

    languages: Set[str] = set()

    for file_path in [prose_path, contracts_path]:
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        sections = _extract_sections_by_unit_heading(text)
        if unit_number in sections:
            section_text = sections[unit_number][1]
            languages |= _detect_languages_in_text(section_text)

    return languages
