# Spirit Caller `.ydc` format investigation (EUR)

This is an isolated, **read-only** investigation of deck resources in a
personally dumped EUR copy of *Yu-Gi-Oh! GX Spirit Caller*. It is not part of
the source-matching pipeline, and changes no code, linkage, symbols or ROMs.
It requires Python 3.9+ and no additional dependencies.

```sh
python contrib/ydc/inspect.py orig/baserom_eur.nds --stats
python contrib/ydc/inspect.py orig/baserom_eur.nds --list
python contrib/ydc/inspect.py orig/baserom_eur.nds --deck SS0102 --json
python -m unittest discover -s tests -p test_ydc_inspect.py
```

The parser reads the NitroFS FNT/FAT in the NDS header, locates `deck/*.ydc`
and parses each file. It never writes to its input and bundles **no** game
binary data, extracted decks, card lists or decryption keys.

## Observed layout

| Offset | Encoding | Description | Confidence |
|---|---|---|---|
| `0x00` | 8 raw bytes | Opaque header; **meaning unknown** | High (size) |
| `0x08` | `u16` little-endian | Count of section 1 (tentatively **main**) | High |
| `0x0A` | `count1 * u16` | Section 1 card identifiers | High |
| variable | `u16` LE + `count2 * u16` | Section 2 (tentatively **extra/fusion**) | High layout; unverified meaning |
| variable | `u16` LE + `count3 * u16` | Section 3 (tentatively **side**) | High layout; unverified meaning |
| EOF | — | Exactly at the end of section 3 | High for the tested ROM |

No alignment padding has been observed. Repeated card IDs are preserved. These
are raw *in-game* numeric identifiers, **not** the printed eight-digit Yu-Gi-Oh!
card passcodes. The semantic names `main`, `extra`, `side` are hypotheses,
not proven by identifying the game routines that load these sections.

## EUR observations (local ROM, SHA-1 verified by repository)

The EUR ROM with SHA-1 `1da50df7c210fae96dc69b3825554b9ce13b4f75`
contains **143** `deck/*.ydc` files in NitroFS, including `deck/default.ydc`.
All 143 parse completely with this layout; this is format validation, **not**
proof of game semantics.

- 134 files have opaque prefix `01fc12004f57443f`; 9 have
  `01cccccc7f217741`. The significance is unknown.
- Section 1 counts: 124 decks with 40 entries, 15 with 41, and one each
  with 43, 44, 64 and 67 entries.
- Section 2 ranges from 0 to 20 entries, and is empty in 113 files.
- Section 3 is empty in all 143 EUR files. A nonempty third section is accepted
  by the parser and exercised by a synthetic test, but its interpretation
  **cannot be confirmed** using this ROM alone.
- Unusual section 1 lengths are **observations**, not necessarily defects or
  illegal decks (the game rules and any unused resource files differ).

## Verification and open questions

```sh
python -m pytest -q tests/test_ydc_inspect.py
python -m unittest discover -s tests -p test_ydc_inspect.py
```

Synthetic tests cover duplicate IDs, both prefixes, empty/nonempty sections,
truncation, wrong counts, extra bytes, NitroFS FNT/FAT, cycles and bad files.
Running `--stats` against a personally supplied EUR ROM independently checks
all 143 deck files. Do not commit ROMs, extracted binary decks or generated
deck/card databases.

Unresolved: meaning of the two prefix variants; confirming section semantics
from loader functions; mapping deck filename to an NPC; mapping internal card
IDs to display names. None of these is asserted by this initial reader.

For upstream integration, first confirm the maintainer wants a separate
research utility: the main project deliberately retired much exploratory
tooling in its September 2026 housekeeping.
