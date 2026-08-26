---
phase: 03
slug: icao-driven-build
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-25
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — tests/ discovered by default |
| **Quick run command** | `venv/Scripts/python.exe -m pytest tests/test_build_icao.py tests/test_icao.py -q` |
| **Full suite command** | `venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~1 second (54 tests) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01 | 01 | 1 | BUILD-02 | — | Single ICAO resolves and builds its containing tile | unit | `pytest tests/test_build_icao.py::test_dispatch_single_icao_builds_containing_tile -q` | ✅ | ✅ green |
| 03-01 | 01 | 1 | BUILD-03 | — | `--radius N` Chebyshev square, negative coords, antimeridian wrap, pole skip, dedupe | unit | `pytest tests/test_build_icao.py -k neighbor -q` | ✅ | ✅ green |
| 03-01 | 01 | 1 | BUILD-04 | T-03-02/T-03-03 | Multiple ICAOs; unknown skipped, unreachable aborts before build, per-tile failure continues | unit | `pytest tests/test_build_icao.py -k batch -q` | ✅ | ✅ green |
| 03-01 | 01 | 1 | BUILD-05 | T-03-01 | List file, `#`/blank lines ignored, missing/empty file exits clean | unit | `pytest tests/test_build_icao.py -k parse_icao_args -q` | ✅ | ✅ green |
| 03-02 | 02 | 1 | BUILD-03/BUILD-04 | T-03-03 | Real server `AIRPORT_NOT_FOUND` skips ICAO, still builds resolvable tile, exits 1 (G-03-7) | unit | `pytest tests/test_build_icao.py::test_batch_unknown_icao_real_resolver_skips_and_summarizes -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--radius 1` runs 9 real full tile builds end-to-end | BUILD-03 | Each build downloads imagery/DEM and shells to native binaries (~minutes/tile); the tile-set expansion itself is unit-tested via `neighbor_tiles` | Run `python Ortho4XP.py build --icao KJFK --radius 1` with a provider/zl and confirm 9 deduped tiles build (UAT test 5, skipped for speed) |
| Live aviation-server smoke of the unknown-ICAO skip path | BUILD-04 | Needs the real mcp_aviation_server up; the code path is unit-tested via a real-resolver monkeypatched transport | `python Ortho4XP.py build --icao ZZZZ,KJFK` → skips ZZZZ, builds +40-074, exits 1 (UAT test 7 — passed manually 2026-08-25) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none)
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-25

---

## Validation Audit 2026-08-25

| Metric | Count |
|--------|-------|
| Requirements | 4 (BUILD-02..05) |
| Covered | 4 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

State B reconstruction: all 4 phase requirements map to existing automated tests
(`tests/test_build_icao.py`, `tests/test_icao.py`). Full suite 54 passed. No gaps —
nyquist-compliant without new test generation.
