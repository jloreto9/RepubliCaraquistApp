# Project: RepubliCaraquistApp Technical & Sabermetric Audit

## Architecture
- Streamlit Multi-page Web Application (`🏠_Home.py`, `pages/1_...` to `pages/8_...`)
- Backend & Data Layer: `utils/supabase_client.py`, `utils/analytics.py`, `scripts/update_daily.py`, MLB Stats API integration
- Visual & UI Layer: Custom Dark Navy theme, Plotly charts, UI glossaries / legends
- Test Suite: `tests/` directory (analyzed and verified)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1 Architecture & Syntax | Compilability, circular imports, unused imports, dependency declaration in requirements.txt | M1 (Survey) | ORIGINAL_REQUEST §R1 |
| 2 | R2 Sabermetric & Data Integrity | Mathematical correctness of wOBA, WPA, LI, FIP, LOB, defense, splits, NaN/Inf handling, Supabase/API resilience | M1 (Survey) | ORIGINAL_REQUEST §R2 |
| 3 | R3 Performance, Cache & UI/UX | `st.cache_data` TTL & invalidation, presentation/data separation, Plotly theme contrast, Spanish glossaries | M1 (Survey) | ORIGINAL_REQUEST §R3 |
| 4 | Test Suite Execution | Execution and status documentation of `tests/` suite and sanity checks | M2 (Validation) | ORIGINAL_REQUEST §Verification |
| 5 | R4 Comprehensive Audit Report | Structured Markdown audit report classified by severity (Crítico, Advertencia, Optimización) with verified evidence | M3 (Reporting) | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Survey Exploration (R1, R2, R3) | 3 parallel Explorers analyzing syntax, data integrity, and UI/performance | none | DONE |
| 2 | Test Execution & Verification | Running existing test suite and empirical verification commands | M1 | DONE |
| 3 | Synthesis & Audit Report Formulation | Generating comprehensive report draft with root cause & recommendations | M1, M2 | DONE |
| 4 | Review, Adversarial & Forensic Verification | Independent Reviewers, Challenger verification, Forensic Audit | M3 | DONE |

## Code Layout (Target App)
- `🏠_Home.py`: Entrypoint
- `pages/`: Subpages (1_Standings, 2_Estadisticas_Individuales, 3_Estadisticas_Colectivas, 4_Analisis_WPA, 5_Spray_Charts, 6_Disciplina_y_Zonas, 7_Situacional_y_BvP, 8_Bullpen_y_Lineups)
- `utils/`: `supabase_client.py`, `analytics.py`, `wpa_engine.py`, `elo.py`, `styles.py`, etc.
- `scripts/`: Ingestion & maintenance scripts (`update_daily.py`, `backfill_elo.py`, `elo_sanity_check.py`)
- `requirements.txt`: Project dependencies
- Final Audit Deliverable: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/AUDIT_REPORT_REPUBLICA_CARAQUISTA.md`
