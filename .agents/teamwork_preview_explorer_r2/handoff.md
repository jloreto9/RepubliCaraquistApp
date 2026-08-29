# Handoff Report — Explorer R2: Sabermetrics & Data Flow Integrity Audit

**Date**: 2026-08-29T00:50:00Z  
**Author**: Explorer R2 (Sabermetrics & Data Flow Integrity Auditor)  
**Target Codebase**: `c:/Users/Administrator/Projets/RepubliCaraquistApp`  
**Milestone**: M1 — Survey & Integrity Diagnosis  
**Integrity Mode**: Read-Only (Zero Code Modifications)

---

## 1. Observation

A forensic, line-by-line static analysis was conducted across all Python modules (`🏠_Home.py`, `Home.py`, `app.py`, `pages/*.py`, `utils/*.py`, `scripts/*.py`). The direct code observations are documented below:

### 1.1. Sabermetric Formulas & Mathematical Implementation

1. **OBP Formula in `utils/supabase_client.py:556` and `utils/supabase_client.py:670`**:
   - Lines 545-551:
     ```python
     if 'hbp' in df.columns:
         agg_dict['hbp'] = 'sum'
     if 'sf' in df.columns:
         agg_dict['sf'] = 'sum'
     ```
   - Lines 556-557:
     ```python
     grouped['avg'] = (grouped['h'] / grouped['ab']).fillna(0).round(3)
     grouped['obp'] = ((grouped['h'] + grouped['bb']) / (grouped['ab'] + grouped['bb'])).fillna(0).round(3)
     grouped['slg'] = ((grouped['h'] + grouped['doubles'] + 2*grouped['triples'] + 3*grouped['hr']) / grouped['ab']).fillna(0).round(3)
     ```
   - *Observation*: OBP excludes `hbp` (Hit By Pitch) and `sf` (Sacrifice Flies) in the denominator and numerator, violating the standard MLB/sabermetric definition $\text{OBP} = \frac{H + BB + HBP}{AB + BB + HBP + SF}$.

2. **Unweighted Average of Rate Stats (Simpson's Paradox) in `pages/2_⚾_Estadisticas_Individuales.py:885, 898, 901`**:
   - Lines 885, 898, 901:
     ```python
     team_avg = batting_df['avg'].mean() if 'avg' in batting_df.columns else 0
     ...
     team_era = pitching_df['era'].mean() if 'era' in pitching_df.columns else 0
     ...
     team_whip = pitching_df['whip'].mean() if 'whip' in pitching_df.columns else 0
     ```
   - *Observation*: The team overview cards calculate team AVG, ERA, and WHIP as the simple unweighted arithmetic mean (`.mean()`) of individual player rates, giving equal weight to a reliever with 0.1 IP as a starter with 60.0 IP.

3. **RE24 Base State Binary Encoding Inversion in `utils/wpa_engine.py:18-36`**:
   - RE24 Dictionary definition (lines 17-28):
     ```python
     # Base states: 0: ---, 1: 1--, 2: -2-, 3: --3, 4: 12-, 5: 1-3, 6: -23, 7: 123
     RE24: Dict[Tuple[int, int], float] = {
         (0, 0): 0.461, (0, 1): 0.831, (0, 2): 1.068, (0, 3): 1.350,
         (0, 4): 1.373, (0, 5): 1.640, (0, 6): 1.880, (0, 7): 2.192, ...
     }
     ```
   - Binary encoding function (lines 34-36):
     ```python
     def encode_base_state(on_1b: bool, on_2b: bool, on_3b: bool) -> int:
         """Codifica el estado de bases en un entero de 0 a 7"""
         return int(bool(on_1b)) * 1 + int(bool(on_2b)) * 2 + int(bool(on_3b)) * 4
     ```
   - *Observation*: Binary arithmetic produces `on_3b=True -> state 4` and `on_1b=True, on_2b=True -> state 1 + 2 = 3`. However, in the `RE24` dictionary table, key `3` is assigned `1.350` (runner on 3B) and key `4` is assigned `1.373` (runners on 1B and 2B). Thus, State 3 (`--3`) and State 4 (`12-`) are transposed during RE24 matrix lookups.

4. **Missing Advanced Pitching & Batting Metrics (`wOBA`, `FIP`, `xERA`)**:
   - In `utils/supabase_client.py` and `pages/2_⚾_Estadisticas_Individuales.py`, `wOBA`, `FIP`, and `xERA` are not computed or displayed.
   - `BABIP` is implemented in `utils/spray_chart.py:551` (`(H - HR) / (BIP - HR)`) and retrieved in `pages/3_📊_Estadisticas_Colectivas.py` via MLB Stats API.

5. **Pythagorean Expectation Zero Division in `pages/1_📊_Standings.py:494, 529`**:
   - Lines 494, 529:
     ```python
     pyth_pct = (cf**1.83) / ((cf**1.83) + (cp**1.83))
     ...
     pyth_display['pyth_fmt'] = pyth_display['pyth_pct'].apply(lambda x: f".{int(x*1000):03d}")
     ```
   - *Observation*: If `cf == 0` and `cp == 0` (e.g. before games are played or on zero runs), `pyth_pct` evaluates to `NaN`. Calling `int(NaN * 1000)` on line 529 triggers an unhandled `ValueError: cannot convert float NaN to integer`.

6. **LOB Tracker Event Edge Cases in `utils/situational.py:311-321`**:
   - Line 311:
     ```python
     is_out_event = ~df["is_hit"] & ~df["is_walk"] & ~df["is_hbp"]
     ```
   - *Observation*: Non-out reaching events (such as `Field Error` or `Fielders Choice`) evaluate to `is_out_event = True`. When this occurs with 2 outs, `is_inning_ending_out` evaluates to `True` even though the inning remained active.

7. **Day vs. Night Split Cutoff in `utils/supabase_client.py:238`**:
   - Lines 237-238:
     ```python
     vet_dt = dt - timedelta(hours=4)
     is_night = (vet_dt.hour >= 19)
     ```
   - *Observation*: Games starting between 17:00 and 18:59 VET (e.g., Saturday 6:00 PM twilight/night starts) are classified as Day games.

---

### 1.2. Data Flow & Numerical Resilience

1. **`NaN` vs `Inf` Handling in `utils/supabase_client.py:629-630`**:
   - Lines 629-630:
     ```python
     grouped['era'] = ((grouped['er'] * 9) / grouped['ip']).fillna(0).round(2)
     grouped['whip'] = ((grouped['h'] + grouped['bb']) / grouped['ip']).fillna(0).round(2)
     ```
   - *Observation*: When `ip == 0` and `er > 0` or `h + bb > 0`, pandas float division returns `np.inf`. `.fillna(0)` leaves `np.inf` intact, causing potential sorting or formatting anomalies.

2. **Rate Statistic String Formatting Overflow in `pages/2_⚾_Estadisticas_Individuales.py:125` & `utils/situational.py:349`**:
   - `f".{int(avg * 1000):03d}"` produces `.1000` (4 decimal characters) when `avg == 1.0`. `🏠_Home.py:457` correctly avoids this with `if x < 1 else "1.000"`.

3. **Defensive Data Robustness**:
   - `utils/supabase_client.py:846-880` implements safe converters `_to_int` and `_to_float` with fallback defaults, successfully insulating the application from malformed API payloads.

---

### 1.3. Supabase & MLB Stats API Integration & Security

1. **Read-Only Operation Enforcement**:
   - `utils/supabase_client.py`, `utils/wpa_engine.py`, and all web page controllers only execute `.select()` queries on Supabase tables. No database mutations (`insert`, `update`, `delete`, `upsert`) occur within the user-facing Streamlit app.
2. **Network Resilience & Timeouts**:
   - All external HTTP calls via `requests.get()` across `utils/` specify explicit timeouts (15s to 30s) and bounded `ThreadPoolExecutor` workers (10-12).
3. **Security & Secrets**:
   - `.streamlit/secrets.toml` is ignored via `.gitignore` (line 16).
   - No hardcoded API keys or Supabase service keys exist in Python source files. Credentials resolve strictly through `st.secrets` and `os.environ`.

---

## 2. Logic Chain

```
[Observation 1.1.1] OBP in utils/supabase_client.py:556 uses (h + bb) / (ab + bb)
  └── [Inference] Players with HBP or SF have distorted OBP metrics that do not match official LVBP / MLB records.

[Observation 1.1.2] pages/2_⚾_Estadisticas_Individuales.py:885, 898, 901 calculates team rates using .mean() on player rate columns
  └── [Inference] Violates harmonic/weighted aggregation principles (Simpson's Paradox). Pitchers with 0.1 IP skew the team ERA and WHIP metrics.

[Observation 1.1.3] encode_base_state assigns 3 to (1B+2B) and 4 to (3B), while RE24 dictionary keys assign 3 to (--3) and 4 to (12-)
  └── [Inference] Run Expectancy lookups for situations with runner on 3B vs runners on 1B & 2B are transposed, introducing subtle distortion into WPA and Leverage Index calculations for those two specific base states.

[Observation 1.1.5] pyth_pct division on 0 runs produces NaN, followed by int(NaN * 1000)
  └── [Inference] Opening day or unplayed season queries on Pythagorean tab will raise unhandled ValueError in Streamlit UI.

[Observation 1.2.1] (er * 9) / ip produces np.inf when ip == 0 and er > 0, which .fillna(0) ignores
  └── [Inference] Relief pitchers who allow runs without recording an out retain inf values in ERA/WHIP columns.

[Observation 1.3.1 - 1.3.3] All Supabase queries in web app use .select(); all requests have timeouts; secrets strictly via env
  └── [Inference] The backend data layer adheres strictly to read-only integrity, robust fault-tolerance, and zero credential leakage.
```

---

## 3. Caveats

1. **No Test Suite Execution**: The codebase currently lacks an automated `tests/` directory; findings are grounded in static code analysis and mathematical verification.
2. **External API Latency**: MLB Stats API live feed latency may cause minor delays in WPA calculations during concurrent live game queries, mitigated by `st.cache_data(ttl=1800)`.
3. **Database Schema Constraints**: `scripts/update_daily.py` handles potential missing columns (`phase`, `series_description`) gracefully through exception fallback.

---

## 4. Conclusion

RepubliCaraquistApp demonstrates high architectural resilience, strict read-only compliance in its presentation layer, zero hardcoded credentials, and bounded network operations.

However, the audit identified **6 concrete mathematical and numerical integrity improvements**:
1. **[CRITICAL] Transposed Base States in RE24**: Align `encode_base_state` in `utils/wpa_engine.py` so that binary values match RE24 dictionary keys (or align dictionary keys to binary encoding).
2. **[CRITICAL] Team Rate Stats Calculation**: Replace `.mean()` on rate stats (`avg`, `era`, `whip`) in `pages/2_⚾_Estadisticas_Individuales.py` with volume-weighted sums ($\frac{\sum H}{\sum AB}$, $\frac{\sum ER \times 9}{\sum IP}$, $\frac{\sum (H+BB)}{\sum IP}$).
3. **[HIGH] OBP Formula Correction**: Update `get_batting_stats` in `utils/supabase_client.py` to $\frac{H + BB + HBP}{AB + BB + HBP + SF}$.
4. **[HIGH] Infinite Value Sanitization**: Add `.replace([np.inf, -np.inf], 0)` or `np.where(ip > 0, ...)` for ERA/WHIP calculations in `utils/supabase_client.py`.
5. **[MEDIUM] Pythagorean NaN Guard**: Add zero-coalescing guard `pyth_pct = np.where((cf + cp) > 0, (cf**1.83) / (cf**1.83 + cp**1.83), 0.50)` in `pages/1_📊_Standings.py`.
6. **[MEDIUM] Rate Formatter Cap**: Normalize rate string formatters to handle $1.000$ cleanly across all situational and leader modules.

---

## 5. Verification Method

To independently verify all findings:

1. **Inspect OBP and Rate calculations**:
   - `utils/supabase_client.py` lines 555–558, 629–631, 669–673.
   - `pages/2_⚾_Estadisticas_Individuales.py` lines 885, 898, 901.
2. **Inspect RE24 Base State Lookup**:
   - `utils/wpa_engine.py` lines 18–28 vs lines 34–36.
   - Evaluate `encode_base_state(False, False, True)` (= 4) vs `RE24[(0, 4)]` (= 1.373, which represents 1st & 2nd).
3. **Inspect Pythagorean Division**:
   - `pages/1_📊_Standings.py` lines 494 and 529 with $CF=0, CP=0$.
4. **Inspect Security and Client Permissions**:
   - Verify `utils/supabase_client.py` contains only `.select()` methods.
   - Verify `.gitignore` contains `.streamlit/secrets.toml`.
