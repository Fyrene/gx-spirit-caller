# 15 — Standalone EUR .ydc inspection

## Done

- Added independent, read-only NitroFS/.ydc inspector under `contrib/ydc/`.
- Documented observed deck layout, including unknown header semantics and
  tentative section labels.
- Added `encode_ydc()` and the `--verify-roundtrip` byte-for-byte validator.
- Resolved all 916 unique EUR deck IDs to local names in seven languages via
  CARD_Prop, CARD_Indx_<language> and CARD_Name_<language>.
- Added `--card <ID> --language F` and `--deck <name> --names` commands;
  no card data is committed.
- Added fourteen synthetic card-table tests.
- Added synthetic tests for malformed data and strict round-trip equality,
  including a negative control which injects one wrong byte and verifies detection.
- No changes to build, matcher, ARM source, symbols, delinks or baselines.

## Checked

- `python -m unittest -q tests/test_ydc_card_names.py`: 14 passed locally.
- Local EUR ROM: 1,459 names per language, seven language variants; all
  916 distinct deck IDs resolved with zero missing in each.
- `python -m pytest -q tests/test_ydc_inspect.py`: 22 passed, 25 subtests.
- `python -m unittest discover -s tests -p test_ydc_inspect.py`: 22 passed.
- `python -m py_compile contrib/ydc/inspect.py`: passed.
- `python contrib/ydc/inspect.py <owned EUR .nds> --verify-roundtrip`: 143/143
  deck files reproduced byte-identically (14,076 bytes; zero mismatches).
- `python contrib/ydc/inspect.py <owned EUR .nds> --stats`: 143 decks parsed;
  two observed opaque headers; side-section length 0 in all 143 files.

## Not checked

- Repository-wide pytest/unittest/ruff/fw checks (full repository not available
  in the execution environment); the tool and tests are independent.
- USA or JPN versions (not supplied); no claim about their card tables.
  The meaning of the upper three card-property bits and exact loader
  semantics remain unknown.
- Three-ROM rebuild (no source/build-path change; only EUR ROM supplied).

## Failed or blocked

- None after fixing initial synthetic test fixture errors locally. Upstream
  acceptance is not requested; await maintainer interest in standalone research.
