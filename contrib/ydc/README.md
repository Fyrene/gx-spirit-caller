# Spirit Caller `.ydc` format investigation (EUR)

This is an isolated, **read-only** investigation of deck resources in a
personally dumped EUR copy of *Yu-Gi-Oh! GX Spirit Caller*. It is not part of
the source-matching pipeline, and changes no code, linkage, symbols or ROMs.
It requires Python 3.9+ and no additional dependencies.

```sh
python contrib/ydc/inspect.py orig/baserom_eur.nds --stats
python contrib/ydc/inspect.py orig/baserom_eur.nds --list
python contrib/ydc/inspect.py orig/baserom_eur.nds --deck SS0102 --json
python contrib/ydc/inspect.py orig/baserom_eur.nds --verify-roundtrip
python contrib/ydc/inspect.py orig/baserom_eur.nds --card 6313 --language F
python contrib/ydc/inspect.py orig/baserom_eur.nds --deck SS0102 --names --language F
python contrib/ydc/inspect.py orig/baserom_eur.nds --npc 69
python -m unittest discover -s tests -p test_ydc_inspect.py
python -m unittest discover -s tests -p test_ydc_card_names.py
python -m unittest discover -s tests -p test_ydc_characters.py
```

The parser reads the NitroFS FNT/FAT in the NDS header, locates `deck/*.ydc`
and parses each file. `encode_ydc()` reconstructs each resource and preserves
its eight-byte opaque prefix, three length fields, card order and duplicates.
`--verify-roundtrip` compares each rebuilt resource byte for byte with its
original NitroFS bytes, failing immediately on a difference.
It never writes to its input and bundles **no** game
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
All 143 parse completely **and round-trip byte-identically** with this layout.
This is *resource-level* byte perfection for the EUR ROM, **not** the entire
ROM reconstruction or proof of gameplay semantics.

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

## Card ID to localized name resolution (verified on EUR ROM)

The existing game resources provide the join without any external database:

1. `bin/CARD_Prop.bin` has 1,460 eight-byte records, the first being an empty
   sentinel. The **low 13 bits** of the first little-endian halfword hold an
   in-game card ID; the three upper bits are opaque metadata and are masked.
2. `bin/CARD_Indx_<language>.bin` holds 1,461 pairs of little-endian 32-bit
   offsets: the first into `CARD_Name`, the second into `CARD_Desc`. Each
   property record (slot `i`) matches the index record at **the same `i`**;
   the final index record points to the end of the name file.
3. `bin/CARD_Name_<language>.bin` stores NUL-terminated names padded to
   4-byte boundaries. `E/F/G/I/S` decode with Windows-1252; `J/R` use
   Shift-JIS (CP932). The `R` strings retain in-game `$R` reading markup.

This accounts for **1,459 distinct card IDs and nonempty names in each of
seven language variants**, and **all 916 distinct card IDs referenced by the
143 EUR decks**. In-game IDs `4006` and `4007` both display as
`Dragon Blanc aux Yeux Bleus`, showing that display names are not unique
identifiers. Names are decoded only from the locally supplied ROM; no database
or extracted name list is checked into git.

The first 12 cards in `deck/SS0102.ydc` include Elemental Heroes; its second
section includes Fusion monsters such as Flame Wingman/Thunder Giant. That
supports interpreting section 2 as a Fusion/Extra Deck, but does not establish
the unused third section's semantics. The mapping from filename `SS0102` to a
specific NPC remains **unverified**.

The name-table parser rejects malformed counts, offsets, alignment, missing
terminators, nonzero padding, duplicate IDs and invalid encoded strings.
The ordinal/card join is verified by known named exemplars and complete
cross-checks across all seven localized name tables.

## Character/deck filename correlation (inferred, not confirmed at runtime)

The European ROM contains `BSC/CharParam.inc`, a Shift-JIS text resource
with numbered rows; comments identify characters by name. For instance,
index 1 names Yuki Judai (Jaden Yuki), 5 Manjoume Jun (Chazz Princeton),
69 Tanaka Natsuo, and 70 Katou Ryouta. The `SSCCVV.ydc` filenames contain
a two-digit `CC` equal to these character indices, and a two-digit `VV`
representing a deck variant. That interpretation of `VV` as a variant is
supported by multiple decks sharing the same `CC`, but its exact in-game
selection conditions are not yet reversed.

`--npc CC` lists candidate decks and their Japanese source-table name.
The tool reads the table from the ROM, *not* from a hardcoded copy. A script
filename prefix `BSC/UCC_...` independently uses the same character index
scheme for **48 out of 57 numbered deck groups**, providing further evidence
of a shared naming convention. It still does not prove which deck file the
engine chooses during a given duel.

Of **143** EUR deck files, **138** match a named `CharParam` character:
57 numbered deck groups in total, of which 54 have named characters.
The unresolved resources are:

- `deck/SS7101.ydc`: character 71 has no name in CharParam;
- `deck/SS9801.ydc`, `deck/SS9802.ydc`, `deck/SS9901.ydc`:
  character indices 98/99 lack entries in this 96-row table (indices 0–95);
- `deck/default.ydc`: no numeric character prefix.

These are **unresolved**, never automatically attributed to a named NPC.
Mapping the runtime deck loader and variant-selection logic remains future
reverse engineering, outside this independent resource-analysis contribution.

## Verification and open questions

```sh
python -m pytest -q tests/test_ydc_inspect.py
python -m unittest discover -s tests -p test_ydc_inspect.py
```

Synthetic tests cover round-trip equality, duplicate IDs, both prefixes,
empty/nonempty sections, invalid encoder inputs, truncation, wrong counts,
extra bytes, NitroFS FNT/FAT, cycles and bad files. Running
`--verify-roundtrip` against a personally supplied EUR ROM checks all 143
resource files byte for byte. There is no claim that USA/JPN decks or the
full game build are byte-perfect. Do not commit ROMs, extracted binary decks or generated
deck/card databases.

Unresolved: meaning of the two prefix variants; confirming each counted deck
section against the game's loading routines; proving runtime deck selection;
meaning of the high three bits in the card properties. Those items are not
asserted by this standalone investigation.

For upstream integration, first confirm the maintainer wants a separate
research utility: the main project deliberately retired much exploratory
tooling in its September 2026 housekeeping.
