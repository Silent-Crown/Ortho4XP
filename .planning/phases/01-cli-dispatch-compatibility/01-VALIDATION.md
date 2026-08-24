---
phase: 1
slug: cli-dispatch-compatibility
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — project has no test suite (runs from source); Phase 1 validated via manual CLI invocations |
| **Config file** | none |
| **Quick run command** | `python Ortho4XP.py --help` (smoke: argparse tree loads) |
| **Full suite command** | manual CLI matrix (see Manual-Only Verifications) |
| **Estimated runtime** | ~5 seconds (no-build smoke checks) |

---

## Sampling Rate

- **After every task commit:** Run `python Ortho4XP.py --help` and `python Ortho4XP.py build --help`
- **After every plan wave:** Run the manual CLI matrix below
- **Before `/gsd-verify-work`:** All CLI-01..04 manual checks pass
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | REQ-{XX} | T-{N}-01 / — | {expected secure behavior or "N/A"} | manual | `{command}` | ❌ W0 | ⬜ pending |

*Populated by the planner from PLAN.md tasks. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] No test framework to install — validation is manual CLI invocation.

*Existing (source-run) infrastructure covers all phase requirements; no automated harness added this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--help` documents all commands/flags | CLI-01 | No test framework | `python Ortho4XP.py --help` and `python Ortho4XP.py build --help` list every command/flag |
| No-arg launches GUI unchanged | CLI-02 | GUI is Tkinter, manual | `python Ortho4XP.py` (no args) opens the GUI window as before |
| Legacy `lat lon [provider zl]` builds | CLI-02 | Full build is slow/external | `python Ortho4XP.py <lat> <lon>` routes to the legacy build path (dispatch reached; may be cut short pre-download) |
| Negative coords floored to tile | CLI-04 | Numeric edge check | `-0.5` maps to tile `-1`, `47.5` to `47` via `math.floor(float(x))` |
| Failure exits non-zero with real error | CLI-03 | Error path | A forced build/arg failure prints traceback to stderr and exits non-zero (not `print("Crash!")`, not exit 0) |

---

## Validation Sign-Off

- [ ] All CLI-01..04 have a manual verification instruction
- [ ] Sampling continuity: smoke check runnable after every task
- [ ] Wave 0 covers all MISSING references (N/A — no framework)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
