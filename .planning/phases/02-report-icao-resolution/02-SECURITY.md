---
phase: 2
slug: report-icao-resolution
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-24
---

# Phase 2 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI arg → resolver | user-supplied ICAO string crosses into an outbound HTTP request | untrusted short string |
| aviation server → resolver | untrusted JSON/SSE response parsed into coordinates | untrusted JSON payload |
| Tiles/ filesystem → report | tile directory names + per-tile `.cfg` contents read from disk | untrusted filenames + cfg text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-06 | Spoofing | not-found masquerading as success | high | mitigate | Classification keys on inner `code`/`error`, never `isError`; `AIRPORT_DETAILS_ERROR`→`ICAONotFound`, no coordinate ever returned on any error path (`O4_ICAO_Utils.py:84-102`). Verified live during UAT (server returned `isError:false` but error `code`; correctly treated as not-found). | closed |
| T-02-01 | Denial of Service | resolve_icao HTTP calls | medium | mitigate | Explicit `timeout=` (default 10.0) on every POST; single attempt, fail fast (`O4_ICAO_Utils.py:42,61,70,73`). | closed |
| T-02-02 | Tampering | untrusted server payload | medium | mitigate | `airport`/`coordinates` presence checked; lat/lon coerced to float and range/finite-validated via `_valid()` before return; `json.loads` only, no eval (`O4_ICAO_Utils.py:86-95,105-107`). | closed |
| T-02-08 | Tampering | accidental mutation during Tiles/ scan | medium | mitigate | Read-only scan: `os.scandir`/`os.walk`/`getsize`/`getmtime`/`open(...,"r")` only — no write/delete/move/rename anywhere in `O4_Report_Utils.py`. | closed |
| T-02-04 | Tampering | tile dir names / path traversal | low | mitigate | Directory names matched by strict `^zOrtho4XP_([+-]\d{2,})([+-]\d{3,})$` regex; lat/lon are ints; all paths via FNAMES (`O4_Report_Utils.py:14,63`). | closed |
| T-02-05 | Elevation of Privilege | untrusted per-tile `.cfg` content | low | mitigate | `read_cfg` uses plain `split("=",1)`; the legacy exec/eval branch is dropped — values stay strings (`O4_Report_Utils.py:24-29`). | closed |
| T-02-07 | Info disclosure | error messages | low | mitigate | Single-line stderr (server URL + code + short reason); no full traceback to user for the two known failure paths (`O4_Report_Utils.py:219`). | closed |
| T-02-SC | Tampering (supply chain) | pytest dev install | low | mitigate | pytest is a canonical dev-only package; not a runtime dependency; no `[ASSUMED]`/`[SUS]` packages introduced this phase (RESEARCH package-legitimacy audit: no runtime installs). | closed |
| T-02-03 | Info disclosure / SSRF | `mcp_aviation_server_url` | low | accept | URL is operator-set in `Ortho4XP.cfg`, not per-command input; documented as trusted local/LAN endpoint. No per-request URL override this phase. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-02-01 | T-02-03 | Aviation server URL is operator-configured in Ortho4XP.cfg (trusted local/LAN), never per-command input; no per-request override in scope this phase. | DonutATX | 2026-08-24 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-24 | 9 | 9 | 0 | gsd-secure-phase (L1 grep-depth, register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-24
