"""Resolve Spirit Caller in-game card IDs to names from an owned ROM.

No game content is bundled; the upper three bits of each CARD_Prop identifier
halfword are opaque metadata, and must not be mistaken for the card ID.
"""

import struct

LANGUAGES = {
    "E": "cp1252",  # English
    "F": "cp1252",  # French
    "G": "cp1252",  # German
    "I": "cp1252",  # Italian
    "S": "cp1252",  # Spanish
    "J": "cp932",   # Japanese
    "R": "cp932",   # Japanese with pronunciation markup
}


def decode_card_names(properties, indices, names, language="F"):
    """Map internal card ID to localized display name.

    CARD_Prop: 8-byte records, including one initial empty record; the low
      13 bits of the leading little-endian u16 are the internal card ID.
    CARD_Indx: 8-byte (name offset, description offset) pairs, with one
      additional final sentinel; only name offsets are used here.
    CARD_Name: NUL-terminated names, padded to 4-byte boundaries.
    """
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language!r}")
    if len(properties) < 16 or len(properties) % 8:
        raise ValueError("CARD_Prop length must be a multiple of 8 and have cards")
    if len(indices) != len(properties) + 8:
        raise ValueError("CARD_Indx must have one extra 8-byte sentinel")
    entry_count = len(properties) // 8
    offsets = [struct.unpack_from("<I", indices, i * 8)[0]
               for i in range(entry_count + 1)]
    if offsets[-1] != len(names):
        raise ValueError("CARD_Indx final name offset differs from CARD_Name size")

    cards = {}
    for i in range(1, entry_count):
        card_id = struct.unpack_from("<H", properties, i * 8)[0] & 0x1FFF
        start, end = offsets[i:i + 2]
        if start >= end or end > len(names) or start % 4 or end % 4:
            raise ValueError(f"Invalid name offsets for card slot {i}: {start}..{end}")
        block = names[start:end]
        null = block.find(b"\x00")
        if null <= 0 or any(block[null + 1:]):
            raise ValueError(f"Malformed terminated/padded name at slot {i}")
        try:
            name = block[:null].decode(LANGUAGES[language], errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Invalid encoded name at slot {i}") from exc
        if card_id in cards:
            raise ValueError(f"Duplicate card ID {card_id}")
        cards[card_id] = name
    return cards


def read_card_names(rom, nitrofs_entries, language="F"):
    """Use the NitroFS path -> (offset, end) mapping to read three tables."""
    def resource(path):
        if path not in nitrofs_entries:
            raise ValueError(f"Missing NitroFS resource: {path}")
        start, end = nitrofs_entries[path]
        return rom[start:end]

    return decode_card_names(
        resource("bin/CARD_Prop.bin"),
        resource(f"bin/CARD_Indx_{language}.bin"),
        resource(f"bin/CARD_Name_{language}.bin"),
        language,
    )
