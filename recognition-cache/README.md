# Recognition cache

Reference images for the D2R gear-recognition skills (`d2r-gear-recognition` and its category skills).

- `index.json`: one entry per reference (name, category, file, sha256, phash, dhash, source, added).
- `sources.json`: curated source allowlist; entries added only with Nic's approval.
- `tools/gearcache.py`: `add`, `match`, `grid`. Run from the repo root with `--cache recognition-cache`. Needs `pip install imagehash`.
- `<category>/`: normalised reference images.

Match score = phash + dhash Hamming distance; default threshold 24.
Calibration (stash screenshot, 2026-10-10): rune cells 8–21; non-rune cells (gems, charms, empty) 40+.
