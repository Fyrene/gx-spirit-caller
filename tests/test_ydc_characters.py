"""Synthetic character index tests; does not require the game ROM."""

import unittest

from contrib.ydc.characters import (
    match_deck_characters,
    parse_character_parameters,
    read_character_parameters,
)


class CharacterMappingTests(unittest.TestCase):
    @staticmethod
    def sample():
        return (
            "// source generator comment\r\n"
            "{ -1, },\r\n"
            "{ 0, 1, }, // 1 遊城 十代\r\n"
            "{ -1, },\r\n"
            "{ 1, 0, 12, }, // 3 加藤\r\n"
        ).encode("cp932")

    def test_japanese_indexing(self):
        self.assertEqual(
            parse_character_parameters(self.sample()),
            {1: "遊城 十代", 3: "加藤"},
        )

    def test_candidates_and_unresolved(self):
        paths = [
            "deck/SS0101.ydc",
            "deck/SS0102.ydc",
            "deck/SS0305.ydc",
            "deck/SS0401.ydc",
            "deck/default.ydc",
            "deck/SS0101.bin",
            "other/SS0101.ydc",
        ]
        actual = match_deck_characters(paths, {1: "Jaden", 3: "Katou"})
        self.assertEqual(len(actual), 5)
        self.assertEqual(actual[0]["character_name_ja"], "Jaden")
        self.assertEqual(actual[1]["variant"], 2)
        self.assertEqual(actual[2]["character_name_ja"], "Katou")
        self.assertEqual(actual[3]["association"], "unresolved")
        self.assertIsNone(actual[4]["character_id"])

    def test_reject_comment_index_mismatch(self):
        bad = b"{ -1, },\n{ 0, }, // 2 Someone\n"
        with self.assertRaisesRegex(ValueError, "does not match"):
            parse_character_parameters(bad)

    def test_reject_non_cp932_input(self):
        with self.assertRaisesRegex(ValueError, "CP932"):
            parse_character_parameters(b"\x81")

    def test_reject_empty_table(self):
        with self.assertRaisesRegex(ValueError, "No CharParam"):
            parse_character_parameters(b"// only comments\n")

    def test_reject_invalid_row(self):
        with self.assertRaisesRegex(ValueError, "Malformed"):
            parse_character_parameters(b"{ invalid, }, // 0 Test\n")

    def test_reject_non_bytes(self):
        with self.assertRaisesRegex(ValueError, "must be bytes"):
            parse_character_parameters("foo")

    def test_lookup_from_rom(self):
        data = self.sample()
        rom = b"HEADER" + data + b"TAIL"
        self.assertEqual(
            read_character_parameters(rom, {"BSC/CharParam.inc": (6, 6 + len(data))}),
            {1: "遊城 十代", 3: "加藤"},
        )

    def test_reject_missing_resource(self):
        with self.assertRaisesRegex(ValueError, "Missing NitroFS"):
            read_character_parameters(b"", {})


if __name__ == "__main__":
    unittest.main()
