---
phase: 03
slug: icao-driven-build
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-25
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI args / `--icao-file` contents → parser/orchestrator | User-supplied local input (codes, arbitrary file path + file lines) crosses into the program. Local, not a network trust boundary. | ICAO tokens, filesystem path |
| ICAO tokens → aviation server (`resolve_icao`) | Normalized idents flow into HTTP JSON-RPC requests to mcp_aviation_server. | ICAO idents (validated finite/in-range) |
| Aviation server response → coordinates → `run_build` | Network-sourced coordinates and error `code` strings drive which tiles build and skip-vs-abort control flow. | lat/lon floats, server error codes |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering/Input | `parse_icao_args` reading `--icao-file` | medium | mitigate | `open()` wrapped in `except OSError` → one clean stderr line + `sys.exit(1)`, no traceback. `src/O4_CLI_Utils.py:80-96` | closed |
| T-03-02 | Tampering/Input | ICAO token from args/file → resolver | medium | mitigate | Tokens stripped, empties dropped; `resolve_icao` length-guards/normalizes; `except (ICAONotFound, ValueError)` skips-and-summarizes the ident (D-10), never crashes the batch. `src/O4_CLI_Utils.py:88-127` | closed |
| T-03-03 | Denial of Service/Availability | Batch resolution loop vs. dead / erroring server | high | mitigate | All idents resolved before any build; `except AviationServerUnreachable` → `sys.exit(1)` before the build loop, so no partial builds (D-11). Unrecognized/future server error codes fail closed onto this abort branch. `src/O4_CLI_Utils.py:118-131`, `src/O4_ICAO_Utils.py:110-112` | closed |
| T-03-04 | Information Disclosure | File path / server URL echoed in error text | low | accept | Local single-user CLI tool, no auth/secrets/PII; surfacing the path/URL aids debugging. | closed |
| T-03-SC | Tampering (supply chain) | package installs | low | accept | No new dependency added — stdlib `argparse` + already-vendored `requests` only; no package-install task. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `high` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-03-01 | T-03-04 | Local single-user CLI; no secrets/PII. Echoing the offending path/URL in stderr is a debugging aid, not a disclosure. | DonutATX | 2026-08-25 |
| R-03-02 | T-03-SC | No new dependency introduced; stdlib + vendored `requests` only. No install surface to compromise. | DonutATX | 2026-08-25 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-25 | 5 | 5 | 0 | /gsd-secure-phase (L1 grep verification) |

Note: the G-03-7 fix (plan 03-02) reinforces T-03-03 — `resolve_icao` now routes the real
server code `AIRPORT_NOT_FOUND` to `ICAONotFound` (skip path), while every unrecognized code
still falls through to the `AviationServerUnreachable` abort branch (fail-closed default).

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-25
