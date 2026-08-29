# Task Assignment — Explorer R3: Performance, Caching, Architecture & UI/UX

## Mission
Perform a rigorous, read-only audit of `RepubliCaraquistApp` performance, caching, and UI/UX:
1. Caching & Performance:
   - Audit all uses of `@st.cache_data` and `@st.cache_resource` across the codebase.
   - Check TTL values, cache key hashing, mutation of cached objects (unintentional side effects).
   - Check execution bottlenecks, redundant API calls, and data loading separation from UI layout.
2. UI/UX & Theming:
   - Theme consistency: Dark Navy (`#070B19` / `#0D152B`), Caraquista gold accents (`#FDB827`).
   - Plotly visualizations: Contrast, background colors, axis readability, hover labels, responsive margins, color palette consistency.
   - Mobile and desktop responsiveness.
3. Educational Quality & Usability:
   - Verify presence, completeness, and clarity of `📖 Guía y Glosario` expanders across all 8 pages.
   - Language compliance: 100% Spanish labels, tooltips, and explanatory text.

## Target Project
- Path: `c:/Users/Administrator/Projets/RepubliCaraquistApp`
- Working directory: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/teamwork_preview_explorer_r3/`
- Original Request: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/ORIGINAL_REQUEST.md`
- Project Scope: `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/PROJECT.md`

## Constraints & Rules
- STRICTLY READ-ONLY. Do not modify, create, or delete source code files in RepubliCaraquistApp.
- Follow GEMINI.md and CLAUDE.md conventions.
- Write your findings and final report to `c:/Users/Administrator/Projets/RepubliCaraquistApp/.agents/teamwork_preview_explorer_r3/handoff.md`.
- Maintain `progress.md` with timestamps.
- Include precise file paths, line numbers, and UI recommendations.
