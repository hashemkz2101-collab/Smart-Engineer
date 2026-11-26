# File requirements: gap analysis (DEC-023, owner message of 2026-11-24)

Status words: **implemented**, **partial**, **needs development**. No FEATURE_REGISTRY
status was changed by this document.

| # | Owner requirement | State | Notes |
|---|---|---|---|
| 1 | Formats: PDF, DXF, DWG, IFC, XLSX (XLS, CSV), DOCX (DOC); no macro files | implemented (P1-19) | Detected from bytes; DOCM/XLSM and legacy macro files refused (`macro_not_allowed`). |
| 2 | Per-type reading, extraction, analysis | needs development | Files are stored and downloadable only. Belongs with DOC-001, BIM-003 (IFC import, Phase 5), AI-002 and library choices DEC-027/DEC-029. |
| 3 | Several files per project | implemented | Up to 100 per project. |
| 3 | Cross-file reconciliation and discrepancy flags | needs development | Depends on item 2; engineer review flow to be designed. |
| 4 | Versioning (keep, time, uploader, compare, restore, basis version, impact on takeoff) | implemented for files (P1-20); partial overall | Versions, restore, metadata comparison, basis marker and stale-basis warning exist. Content-level comparison needs FILE-003; linking the basis to real takeoff results waits for the estimate features (CORE-003). |
| 5 | Software independent of uploads | implemented | Nothing in project, requirement or calculation flows requires a file. Reference items are not yet linked to files (REQ-003). |
| 6 | Real type check, scan, block suspicious, unsafe structures, safe originals | implemented in code (P1-21); needs ClamAV deployed on the owner's server | Byte-level type check, EICAR/PDF-active/OOXML-active-content quarantine, archive limits, private storage, and ClamAV scanning with fail-closed pending state and a rescan command. Until clamd is installed and configured, production keeps files `pending`. |

Registry rows added with the owner's approval (2026-11-24): FILE-002 versioning (Phase 1, P1-20),
FILE-003 extraction (Phase 3), FILE-004 cross-file reconciliation (Phase 5). All NOT STARTED.
