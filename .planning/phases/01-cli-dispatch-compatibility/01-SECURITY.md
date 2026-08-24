---
phase: 1
slug: cli-dispatch-compatibility
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-24
---

# Phase 1 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Local invoker (interactive user or unattended script) → `O4_CLI_Utils` argv/coordinate parsing | `argv` content crosses from an external caller into the process. Not a network boundary — the threat model is a malformed/malicious local script argument, not a remote actor. | lat/lon/provider/zl strings (untrusted local input) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | `parse_and_floor_coord()` → `CFG.Tile` → `FNAMES` path construction | medium | mitigate | `parse_and_floor_coord()` (`src/O4_CLI_Utils.py:9-30`) coerces via `float()`, rejects non-finite (`math.isfinite`), floors, and range-validates lat∈[-90,89] / lon∈[-180,179], raising `ValueError` **before** `CFG.Tile` is constructed. Only a floored `int` — never a raw attacker-controlled string — reaches path-building code. Verified in code. | closed |
| T-01-02 | Information Disclosure | `run_and_report()` traceback-to-stderr on crash | low | accept | Intentional per CONTEXT.md/CLI-03: local single-user CLI, no test suite; the traceback goes to the invoking user's own terminal, never a remote client. Diagnostic value outweighs disclosure risk. Below block threshold. | closed |
| T-01-03 | Denial of Service | `build_parser()` usage-error path (`required=True` subparsers) | low | accept | argparse's own `sys.exit(2)` on bad/missing args is the standard CLI failure mode — no resource amplification, persistence, or state change. Below block threshold. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

No package-manager installs occur in this phase (stdlib only: `argparse`, `math`, `traceback`), so no package-legitimacy (`T-01-SC`) row applies.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-02 | Traceback to the invoking user's own terminal is the intended diagnostic behavior for a local CLI (replaces the silent `print("Crash!")`); no remote disclosure path exists. | User (CONTEXT.md decision) | 2026-08-24 |
| AR-02 | T-01-03 | argparse's standard exit-2 usage error is the expected, non-amplifying CLI failure mode. | User (CONTEXT.md decision) | 2026-08-24 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-24 | 3 | 3 | 0 | /gsd-secure-phase (L1, plan-authored register) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-24
