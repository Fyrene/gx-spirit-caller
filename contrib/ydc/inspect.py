#!/usr/bin/env python3
"""Inspect Spirit Caller .ydc decks directly from a user-provided Nintendo DS ROM.

No third-party dependencies. The input is read-only; no ROM is redistributed.
The opaque eight-byte deck prefix is deliberately NOT given a guessed meaning.

Usage:
  python contrib/ydc/inspect.py orig/baserom_eur.nds --stats
  python contrib/ydc/inspect.py orig/baserom_eur.nds --list
  python contrib/ydc/inspect.py orig/baserom_eur.nds --deck SS0102 --json
  python contrib/ydc/inspect.py orig/baserom_eur.nds --verify-roundtrip
  python contrib/ydc/inspect.py orig/baserom_eur.nds --card 6313 --language F
  python contrib/ydc/inspect.py orig/baserom_eur.nds --deck SS0102 --names --language F
"""

import argparse
from collections import Counter
import json
import mmap
from pathlib import Path
import struct


def _u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def parse_ydc(data):
    """Parse the observed layout; section names are working hypotheses.

    Offsets after the eight-byte opaque prefix depend on section lengths.
    Identifiers are raw in-game u16 values, not database card passcodes.
    """
    if len(data) < 14:
        raise ValueError("Deck is too short for the prefix and three counts")
    offset = 8
    sections = []
    for section in ("main", "extra", "side"):
        if offset + 2 > len(data):
            raise ValueError(f"Missing {section} count")
        count = _u16(data, offset)
        offset += 2
        end = offset + 2 * count
        if end > len(data):
            raise ValueError(f"Truncated {section} entries: need {count}")
        sections.append(list(struct.unpack_from(f"<{count}H", data, offset)))
        offset = end
    if offset != len(data):
        raise ValueError(f"Unexpected {len(data) - offset} trailing bytes")
    return {
        "header_hex": bytes(data[:8]).hex(),
        "main_count": len(sections[0]),
        "extra_count": len(sections[1]),
        "side_count": len(sections[2]),
        "main_card_ids": sections[0],
        "extra_card_ids": sections[1],
        "side_card_ids": sections[2],
    }


def encode_ydc(deck):
    """Re-encode a parsed deck, preserving its opaque eight-byte prefix."""
    try:
        header_hex = deck["header_hex"]
        if not isinstance(header_hex, str) or len(header_hex) != 16:
            raise ValueError("header_hex must have exactly 16 hex characters")
        try:
            header = bytes.fromhex(header_hex)
        except ValueError as exc:
            raise ValueError("header_hex is not hexadecimal") from exc
        if len(header) != 8:
            raise ValueError("header_hex must represent exactly 8 bytes")
        result = bytearray(header)
        for section in ("main", "extra", "side"):
            values = deck[f"{section}_card_ids"]
            count = deck[f"{section}_count"]
            if not isinstance(values, (list, tuple)):
                raise ValueError(f"{section}_card_ids must be a sequence")
            if type(count) is not int or count != len(values) or count > 0xFFFF:
                raise ValueError(f"{section}_count does not match card IDs")
            if any(type(card_id) is not int or not 0 <= card_id <= 0xFFFF
                   for card_id in values):
                raise ValueError(f"{section}_card_ids must contain u16 integers")
            result.extend(struct.pack("<H", count))
            result.extend(struct.pack(f"<{count}H", *values))
        return bytes(result)
    except KeyError as exc:
        raise ValueError(f"Missing deck field: {exc.args[0]}") from exc


def verify_deck_roundtrips(rom):
    """Compare parsed/re-encoded deck bytes to each original NitroFS file."""
    files = nds_files(rom)
    verified = 0
    for path in sorted(files):
        if not (path.startswith("deck/") and path.lower().endswith(".ydc")):
            continue
        start, end = files[path]
        original = bytes(rom[start:end])
        try:
            rebuilt = encode_ydc(parse_ydc(original))
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        if rebuilt != original:
            mismatch = next((i for i, (a, b) in
                             enumerate(zip(original, rebuilt)) if a != b),
                            min(len(original), len(rebuilt)))
            raise ValueError(f"{path}: round-trip differs at byte 0x{mismatch:x} "
                             f"(original {len(original)} bytes, rebuilt {len(rebuilt)})")
        verified += 1
    if verified == 0:
        raise ValueError("No deck/*.ydc files found")
    return verified


def nds_files(rom):
    """Return path -> (start, end) for NitroFS FNT and FAT entries.

    Validates bounds and directory cycles; it does not extract any files.
    """
    if len(rom) < 0x50:
        raise ValueError("ROM is too short for the NitroFS header")
    fnt_offset, fnt_size, fat_offset, fat_size = struct.unpack_from("<IIII", rom, 0x40)
    if not (fnt_size >= 8 and fnt_offset + fnt_size <= len(rom)):
        raise ValueError("Invalid NitroFS FNT bounds")
    if fat_offset + fat_size > len(rom) or fat_size % 8:
        raise ValueError("Invalid NitroFS FAT bounds")
    directory_count = _u16(rom, fnt_offset + 6)
    if not (1 <= directory_count <= fnt_size // 8):
        raise ValueError("Invalid NitroFS directory count")

    files = {}
    visiting = set()
    visited = set()

    def walk(dir_id, prefix=""):
        if dir_id in visiting:
            raise ValueError("Cyclic NitroFS directory tree")
        if dir_id in visited:
            raise ValueError("Repeated NitroFS directory")
        index = dir_id - 0xF000
        if not 0 <= index < directory_count:
            raise ValueError("Invalid NitroFS directory ID")
        visiting.add(dir_id)
        table_offset = fnt_offset + 8 * index
        cursor = fnt_offset + _u32(rom, table_offset)
        file_id = _u16(rom, table_offset + 4)
        limit = fnt_offset + fnt_size
        while True:
            if not fnt_offset <= cursor < limit:
                raise ValueError("Unterminated NitroFS directory")
            length = rom[cursor]
            cursor += 1
            if length == 0:
                break
            name_length = length & 0x7F
            if name_length == 0 or cursor + name_length > limit:
                raise ValueError("Invalid NitroFS filename")
            name = bytes(rom[cursor:cursor + name_length]).decode("ascii", "replace")
            cursor += name_length
            if length & 0x80:
                if cursor + 2 > limit:
                    raise ValueError("Missing NitroFS child directory ID")
                child_id = _u16(rom, cursor)
                cursor += 2
                walk(child_id, prefix + name + "/")
            else:
                if 8 * (file_id + 1) > fat_size:
                    raise ValueError("NitroFS file ID exceeds FAT")
                start = _u32(rom, fat_offset + 8 * file_id)
                end = _u32(rom, fat_offset + 8 * file_id + 4)
                file_id += 1
                if not 0 <= start <= end <= len(rom):
                    raise ValueError("Invalid NitroFS file allocation")
                path = prefix + name
                if path in files:
                    raise ValueError("Duplicate NitroFS path")
                files[path] = (start, end)
        visiting.remove(dir_id)
        visited.add(dir_id)

    walk(0xF000)
    return files


def read_decks(rom):
    """Parse all deck/*.ydc files without returning the underlying ROM data."""
    files = nds_files(rom)
    result = {}
    for path in sorted(files):
        if not (path.startswith("deck/") and path.lower().endswith(".ydc")):
            continue
        start, end = files[path]
        try:
            result[path] = parse_ydc(rom[start:end])
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
    return result


def summarize(decks):
    """Compute reproducible aggregate statistics, not individual deck dumps."""
    return {
        "deck_count": len(decks),
        "headers": dict(sorted(Counter(d["header_hex"] for d in decks.values()).items())),
        "main_counts": dict(sorted(Counter(d["main_count"] for d in decks.values()).items())),
        "extra_counts": dict(sorted(Counter(d["extra_count"] for d in decks.values()).items())),
        "side_counts": dict(sorted(Counter(d["side_count"] for d in decks.values()).items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path, help="Your own unmodified .nds ROM")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true", help="Validate and list all decks")
    action.add_argument("--stats", action="store_true", help="Validate and summarize all decks")
    action.add_argument("--verify-roundtrip", action="store_true",
                        help="Require byte-identical parse/encode for every .ydc")
    action.add_argument("--deck", help="Select deck by name, e.g. SS0102")
    action.add_argument("--card", type=int, help="Look up one internal card ID")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    parser.add_argument("--names", action="store_true",
                        help="Include localized card names for --deck")
    parser.add_argument("--language", choices=("E", "F", "G", "I", "S", "J", "R"),
                        default="F", help="Card name language (default: F)")
    args = parser.parse_args()
    if args.names and not args.deck:
        parser.error("--names requires --deck")
    with args.rom.open("rb") as stream:
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as rom:
            if args.verify_roundtrip:
                count = verify_deck_roundtrips(rom)
            else:
                decks = read_decks(rom)
                if args.card is not None or args.names:
                    if __package__:
                        from .cards import read_card_names
                    else:
                        from cards import read_card_names
                    card_names = read_card_names(rom, nds_files(rom), args.language)
    if args.verify_roundtrip:
        print(f"BYTE-PERFECT PASS: {count}/{count} deck/*.ydc files match exactly")
    elif args.stats:
        stats = summarize(decks)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            for key, value in stats.items():
                print(f"{key}: {value}")
    elif args.list:
        rows = [
            {"file": path, "main": deck["main_count"],
             "extra": deck["extra_count"], "side": deck["side_count"],
             "header": deck["header_hex"]}
            for path, deck in decks.items()
        ]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f'{row["file"]:29} main={row["main"]:2} '
                      f'extra={row["extra"]:2} side={row["side"]:2} '
                      f'header={row["header"]}')
            print(f"Validated {len(rows)} .ydc decks")
    elif args.card is not None:
        if args.card not in card_names:
            parser.error(f"Unknown internal card ID: {args.card}")
        card = {"id": args.card, "name": card_names[args.card],
                "language": args.language}
        if args.json:
            print(json.dumps(card, indent=2, ensure_ascii=False))
        else:
            print(f'{card["id"]}: {card["name"]} ({args.language})')
    else:
        path = args.deck if args.deck.endswith(".ydc") else args.deck + ".ydc"
        if not path.startswith("deck/"):
            path = "deck/" + path
        if path not in decks:
            parser.error(f"Deck not found: {path}")
        deck = {"file": path, **decks[path]}
        if args.names:
            for section in ("main", "extra", "side"):
                deck[f"{section}_cards"] = [
                    {"id": card_id, "name": card_names[card_id]}
                    for card_id in deck[f"{section}_card_ids"]
                ]
        print(json.dumps(deck, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
