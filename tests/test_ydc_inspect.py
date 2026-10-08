"""Tests for the standalone NitroFS/.ydc inspector; never require a ROM."""

import struct
import unittest

from contrib.ydc.inspect import (
    encode_ydc, nds_files, parse_ydc, read_decks, summarize,
    verify_deck_roundtrips,
)


PREFIX = bytes.fromhex("01fc12004f57443f")


def fixture_deck(main=(), extra=(), side=(), header=PREFIX):
    parts = [header]
    for ids in (main, extra, side):
        parts.append(struct.pack("<H", len(ids)))
        parts.append(struct.pack(f"<{len(ids)}H", *ids))
    return b"".join(parts)


def fixture_rom(deck=None):
    """Small NitroFS image with one root file and one child deck directory."""
    if deck is None:
        deck = fixture_deck((4006, 4006, 6953), (5001,), ())
    rom = bytearray(0x200 + len(deck))
    struct.pack_into("<IIII", rom, 0x40, 0x80, 0x50, 0xD0, 0x10)
    # Two 8-byte directory records; 0xF000 is root, 0xF001 is deck/.
    struct.pack_into("<IHH", rom, 0x80, 0x10, 0, 2)
    struct.pack_into("<IHH", rom, 0x88, 0x30, 1, 0xF000)
    rom[0x90:0x90 + 9] = b"\x08root.txt"
    rom[0x99:0x99 + 8] = b"\x84deck\x01\xf0\x00"
    rom[0xB0:0xB0 + 12] = b"\x0aSS0101.ydc\x00"
    struct.pack_into("<IIII", rom, 0xD0, 0x100, 0x104, 0x200, 0x200 + len(deck))
    rom[0x200:0x200 + len(deck)] = deck
    return rom


class TestYdcParser(unittest.TestCase):
    def test_three_sections_preserve_order_and_duplicate_ids(self):
        data = fixture_deck((4006, 4006, 6953), (5555,), (6666,))
        parsed = parse_ydc(data)
        self.assertEqual(parsed["header_hex"], PREFIX.hex())
        self.assertEqual(parsed["main_card_ids"], [4006, 4006, 6953])
        self.assertEqual(parsed["extra_card_ids"], [5555])
        self.assertEqual(parsed["side_card_ids"], [6666])
        self.assertEqual((parsed["main_count"], parsed["extra_count"],
                          parsed["side_count"]), (3, 1, 1))

    def test_roundtrip_preserves_duplicate_ids_and_all_sections(self):
        original = fixture_deck((4006, 4006, 0, 65535), (5555,), (1234, 0))
        self.assertEqual(encode_ydc(parse_ydc(original)), original)

    def test_roundtrip_preserves_both_headers(self):
        for header in (PREFIX, bytes.fromhex("01cccccc7f217741")):
            with self.subTest(header=header.hex()):
                original = fixture_deck((4000, 5000), header=header)
                self.assertEqual(encode_ydc(parse_ydc(original)), original)

    def test_encoder_rejects_count_mismatch(self):
        deck = parse_ydc(fixture_deck((1234,)))
        deck["main_count"] = 2
        with self.assertRaisesRegex(ValueError, "main_count"):
            encode_ydc(deck)

    def test_encoder_rejects_invalid_card_ids(self):
        for invalid in (-1, 65536, "1234", 12.3, True):
            with self.subTest(invalid=invalid):
                deck = parse_ydc(fixture_deck((1234,)))
                deck["main_card_ids"][0] = invalid
                with self.assertRaisesRegex(ValueError, "u16"):
                    encode_ydc(deck)

    def test_encoder_rejects_bad_headers(self):
        for invalid in ("ff", "00" * 9, "zz" * 8, "00 00 00 00 00 00 00 0"):
            with self.subTest(invalid=invalid):
                deck = parse_ydc(fixture_deck())
                deck["header_hex"] = invalid
                with self.assertRaises(ValueError):
                    encode_ydc(deck)

    def test_encoder_rejects_missing_fields(self):
        deck = parse_ydc(fixture_deck())
        del deck["side_card_ids"]
        with self.assertRaisesRegex(ValueError, "Missing deck field"):
            encode_ydc(deck)

    def test_alternative_header_remains_opaque(self):
        other = bytes.fromhex("01cccccc7f217741")
        self.assertEqual(parse_ydc(fixture_deck(header=other))["header_hex"], other.hex())

    def test_empty_sections(self):
        self.assertEqual(parse_ydc(fixture_deck())["main_card_ids"], [])

    def test_truncated_file_rejected(self):
        data = fixture_deck((4200,), (5200,))
        for cut in range(14):
            with self.subTest(cut=cut), self.assertRaises(ValueError):
                parse_ydc(data[:cut])
        with self.assertRaises(ValueError):
            parse_ydc(data[:-1])

    def test_fake_count_rejected(self):
        raw = bytearray(fixture_deck((4012,)))
        struct.pack_into("<H", raw, 8, 0xFFFF)
        with self.assertRaisesRegex(ValueError, "Truncated main"):
            parse_ydc(raw)

    def test_trailing_bytes_rejected(self):
        with self.assertRaisesRegex(ValueError, "trailing"):
            parse_ydc(fixture_deck() + b"\x00")


class TestNitroFs(unittest.TestCase):
    def test_nested_directory_and_payload(self):
        rom = fixture_rom()
        files = nds_files(rom)
        self.assertEqual(files["root.txt"], (0x100, 0x104))
        self.assertIn("deck/SS0101.ydc", files)
        decks = read_decks(rom)
        self.assertEqual(list(decks), ["deck/SS0101.ydc"])
        self.assertEqual(decks["deck/SS0101.ydc"]["main_card_ids"],
                         [4006, 4006, 6953])
        self.assertEqual(summarize(decks)["deck_count"], 1)

    def test_byte_perfect_verifier_on_synthetic_rom(self):
        self.assertEqual(verify_deck_roundtrips(fixture_rom()), 1)

    def test_byte_perfect_verifier_rejects_invalid_deck(self):
        with self.assertRaisesRegex(ValueError, "deck/SS0101.ydc"):
            verify_deck_roundtrips(fixture_rom(b"\x00" * 13))

    def test_byte_perfect_verifier_rejects_missing_decks(self):
        rom = bytearray(fixture_rom())
        rom[0xB1:0xB1 + 10] = b"SS0101.bin"
        with self.assertRaisesRegex(ValueError, "No deck"):
            verify_deck_roundtrips(rom)

    def test_truncated_header(self):
        with self.assertRaisesRegex(ValueError, "too short"):
            nds_files(bytes(0x4F))

    def test_fnt_outside_rom(self):
        rom = fixture_rom()
        struct.pack_into("<I", rom, 0x44, 10000)
        with self.assertRaisesRegex(ValueError, "FNT"):
            nds_files(rom)

    def test_fat_outside_rom(self):
        rom = fixture_rom()
        struct.pack_into("<I", rom, 0x4C, 10000)
        with self.assertRaisesRegex(ValueError, "FAT"):
            nds_files(rom)

    def test_child_directory_cycle(self):
        rom = fixture_rom()
        struct.pack_into("<H", rom, 0x9E, 0xF000)
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            nds_files(rom)

    def test_malformed_deck_reports_filename(self):
        rom = fixture_rom(b"\x00" * 13)
        with self.assertRaisesRegex(ValueError, "deck/SS0101.ydc"):
            read_decks(rom)


if __name__ == "__main__":
    unittest.main()
