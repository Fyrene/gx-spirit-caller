"""Identify candidate owners of deck filenames using source tables in the ROM.

This is an evidence-based naming correlation, not proof that the game loads
that deck for the corresponding character. No copyrighted tables are bundled.
"""

import re


_DECK_PATH = re.compile(r"^deck/SS(\d{2})(\d{2})\.ydc$")
_COMMENT = re.compile(r"//\s*(\d+)\s+(.+?)\s*$")


def parse_character_parameters(source):
    """Read character-index comments from BSC/CharParam.inc (Shift-JIS).

    Rows start at zero, including unlabelled sentinels. Comments must agree
    with the actual row number before a name is trusted.
    """
    if not isinstance(source, (bytes, bytearray)):
        raise ValueError("CharParam source must be bytes")
    try:
        lines = source.decode("cp932", "strict").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("CharParam is not valid CP932 text") from exc
    names = {}
    row = 0
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        if not re.match(r"^\{\s*[-\d,\s]+\}\s*,?\s*(?://.*)?$", line):
            raise ValueError(f"Malformed CharParam row {row}")
        comment = _COMMENT.search(line)
        if comment:
            index = int(comment.group(1))
            name = comment.group(2).strip()
            if index != row:
                raise ValueError(f"CharParam row comment {index} does not match {row}")
            if not name:
                raise ValueError(f"Empty CharParam name at {row}")
            names[index] = name
        row += 1
    if row == 0:
        raise ValueError("No CharParam table rows")
    return names


def match_deck_characters(paths, characters):
    """Associate deck SSCCVV names with *candidate* CharParam character CC.

    A missing name stays unresolved; neither an NPC relationship nor the
    meaning of the numeric variant VV is asserted.
    """
    matches = []
    for path in sorted(paths):
        if not (path.startswith("deck/") and path.endswith(".ydc")):
            continue
        match = _DECK_PATH.fullmatch(path)
        if match:
            character_id, variant = (int(v) for v in match.groups())
            character_name = characters.get(character_id)
        else:
            character_id = variant = character_name = None
        matches.append({
            "file": path,
            "character_id": character_id,
            "variant": variant,
            "character_name_ja": character_name,
            "association": "filename_index_match" if character_name else "unresolved",
        })
    return matches


def read_character_parameters(rom, nitrofs_entries):
    """Read the table from the user's ROM, without exporting game assets."""
    path = "BSC/CharParam.inc"
    if path not in nitrofs_entries:
        raise ValueError(f"Missing NitroFS resource: {path}")
    start, end = nitrofs_entries[path]
    return parse_character_parameters(rom[start:end])
