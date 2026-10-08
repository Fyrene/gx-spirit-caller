# 15 — Standalone EUR .ydc inspection

## Done

- Added independent, read-only NitroFS/.ydc inspector under `contrib/ydc/`.
- Documented observed deck layout, including unknown header semantics and
  tentative section labels.
- Added synthetic unit tests for valid decks and malformed data.
- No changes to build, matcher, ARM source, symbols, delinks or baselines.

## Checked

- `python -m pytest -q tests/test_ydc_inspect.py`: 12 passed, 14 subtests.
- `python -m unittest discover -s tests -p test_ydc_inspect.py`: 12 passed.
- `python -m py_compile contrib/ydc/inspect.py`: passed.
- `python contrib/ydc/inspect.py <owned EUR .nds> --stats`: 143 decks parsed;
  two observed opaque headers; side-section length 0 in all 143 files.

## Not checked

- Repository-wide pytest/unittest/ruff/fw checks (full repository not available
  in the execution environment); the tool and tests are independent.
- USA or JPN versions (not supplied); the game's loader semantics and internal
  card-ID-to-name mapping are not established.
- Three-ROM rebuild (no source/build-path change; only EUR ROM supplied).

## Failed or blocked

- None after fixing initial synthetic test fixture errors locally. Upstream
  acceptance is not requested; await maintainer interest in standalone research.
