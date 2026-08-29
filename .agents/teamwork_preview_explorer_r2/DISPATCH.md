# Task Assignment — Explorer R2: Sabermetrics & Data Flow Integrity

## Mission
Perform a rigorous, read-only audit of `RepubliCaraquistApp` data integrity and sabermetric logic:
1. Sabermetric formulas & math verification:
   - wOBA (weights, season constants, plate appearances handling)
   - WPA & Leverage Index (Win Expectancy Matrix, RE24 Tango transitions)
   - FIP, xERA, BABIP, WHIP
   - LOB Tracker (inning ending vs inside inning RISP LOB)
   - Fielding metrics (PO, A, E, TC, FPCT, DP, RF/9, catcher CS, SB, CS%, PB)
   - Situational splits (day vs night records based on VET time, ISO calendar weekly groupings).
2. Data Flow & Numerical Resilience:
   - Division-by-zero, `NaN`, `Inf` handling in pandas / numpy transformations.
   - Type casting safety (int/float conversion issues, `SettingWithCopyWarning`, immutable pandas ops).
   - Data leakage / join validation (avoid duplicate rows or silent row drops).
3. Backend & API Resilience:
   - Supabase client queries (`utils/supabase_client.py`) read-only enforcement, error handling, connection failures.
   - MLB Stats API ingestion handling (`scripts/update_daily.py`, etc.).
   - Credential handling: strictly `.env` / Streamlit secrets, no hardcoded keys.

## Target Project
- Path: `c:/Users/Administrator/Projets/RepubliCaraquistApp`
- Working directory: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/teamwork_preview_explorer_r2/`
- Original Request: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/ORIGINAL_REQUEST.md`
- Project Scope: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/PROJECT.md`

## Constraints & Rules
- STRICTLY READ-ONLY. Do not modify, create, or delete source code files in RepubliCaraquistApp.
- Follow GEMINI.md and CLAUDE.md conventions.
- Write your findings and final report to `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/teamwork_preview_explorer_r2/handoff.md`.
- Maintain `progress.md` with timestamps.
- Include precise file paths, line numbers, and formulas.
