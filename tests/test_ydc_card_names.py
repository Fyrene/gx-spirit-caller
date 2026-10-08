"""Synthetic card-name table tests: no game ROM or extracted tables required."""

import struct
import unittest

from contrib.ydc.cards import decode_card_names, read_card_names


def fixtures(language="F"):
    # One empty property record, followed by two cards with metadata bits.
    prop = bytes(8) + struct.pack("<H6x", 0x8FA6) + struct.pack("<H6x", 0x4FA7)
    encoding = "cp932" if language in ("J", "R") else "cp1252"
    names = ("青眼", "火炎") if language in ("J", "R") else ("Éclair", "Flamme")
    data = bytearray(8)
    offsets = [4, 8]
    for name in names:
        data.extend(name.encode(encoding) + b"\x00")
        data.extend(bytes((-len(data)) % 4))
        offsets.append(len(data))
    indices = b"".join(struct.pack("<II", off, 0) for off in offsets)
    return prop, indices, bytes(data)


class CardNamesTests(unittest.TestCase):
    def test_id_mask_and_french_names(self):
        self.assertEqual(decode_card_names(*fixtures("F"), "F"),
                         {4006: "Éclair", 4007: "Flamme"})

    def test_japanese_cp932(self):
        self.assertEqual(decode_card_names(*fixtures("J"), "J")[4006], "青眼")

    def test_ruby_cp932(self):
        self.assertEqual(decode_card_names(*fixtures("R"), "R")[4007], "火炎")

    def test_english_cp1252(self):
        self.assertEqual(decode_card_names(*fixtures("E"), "E")[4006], "Éclair")

    def test_reject_unsupported_language(self):
        with self.assertRaisesRegex(ValueError, "Unsupported language"):
            decode_card_names(*fixtures(), "FR")

    def test_reject_wrong_prop_size(self):
        properties, indices, names = fixtures()
        with self.assertRaisesRegex(ValueError, "CARD_Prop"):
            decode_card_names(properties[:-1], indices, names)

    def test_reject_wrong_index_size(self):
        properties, indices, names = fixtures()
        with self.assertRaisesRegex(ValueError, "CARD_Indx"):
            decode_card_names(properties, indices[:-8], names)

    def test_reject_wrong_end_marker(self):
        properties, indices, names = fixtures()
        corrupted = bytearray(indices)
        struct.pack_into("<I", corrupted, len(corrupted) - 8, 12)
        with self.assertRaisesRegex(ValueError, "final name offset"):
            decode_card_names(properties, corrupted, names)

    def test_reject_out_of_range_offset(self):
        properties, indices, names = fixtures()
        corrupted = bytearray(indices)
        struct.pack_into("<I", corrupted, 8, 24)
        with self.assertRaisesRegex(ValueError, "Invalid name offsets"):
            decode_card_names(properties, corrupted, names)

    def test_reject_unterminated_name(self):
        properties, indices, names = fixtures()
        corrupted = bytearray(names)
        corrupted[8:16] = b"ABCDEFGH"
        with self.assertRaisesRegex(ValueError, "Malformed terminated"):
            decode_card_names(properties, indices, corrupted)

    def test_reject_padding_corruption(self):
        properties, indices, names = fixtures()
        corrupted = bytearray(names)
        corrupted[15] = ord("A")
        with self.assertRaisesRegex(ValueError, "Malformed terminated"):
            decode_card_names(properties, indices, corrupted)

    def test_reject_duplicate_ids(self):
        properties, indices, names = fixtures()
        corrupted = bytearray(properties)
        struct.pack_into("<H", corrupted, 16, 0x4FA6)
        with self.assertRaisesRegex(ValueError, "Duplicate card ID"):
            decode_card_names(corrupted, indices, names)

    def test_missing_nitrofs_resource(self):
        with self.assertRaisesRegex(ValueError, "Missing NitroFS resource"):
            read_card_names(b"", {})

    def test_resource_lookup(self):
        properties, indices, names = fixtures()
        chunks = (properties, indices, names)
        paths = ("bin/CARD_Prop.bin", "bin/CARD_Indx_F.bin", "bin/CARD_Name_F.bin")
        rom = b"".join(chunks)
        offset = 0
        entries = {}
        for path, data in zip(paths, chunks):
            entries[path] = (offset, offset + len(data))
            offset += len(data)
        self.assertEqual(read_card_names(rom, entries)[4007], "Flamme")


if __name__ == "__main__":
    unittest.main()
