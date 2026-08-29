# Handoff Report — Challenger 1: Empirical Verification & Adversarial Stress Testing

**Verdict:** `APPROVE` (Audit findings verified with 100% empirical reproducibility + 1 critical paired-fix discovery).

---

## 1. Observation

Direct empirical observations, verbatim terminal outputs, and code references gathered across the 4 validation targets:

### Observation 1.1: `scripts/update_daily.py` Import Failure
* **Command executed:** `python scripts/update_daily.py` from repository root (`c:/Users/Administrator/Projets/RepubliCaraquistApp`).
* **Verbatim Terminal Output:**
  ```text
  Traceback (most recent call last):
    File "C:\Users\Administrator\Projets\RepubliCaraquistApp\scripts\update_daily.py", line 7, in <module>
      from utils.elo import BASE_ELO, HOME_ADVANTAGE, K_BY_PHASE, update_elo
  ModuleNotFoundError: No module named 'utils'
  ```
  *(Exit code: `1`)*
* **Fix Validation Command:**
  ```powershell
  python -c "import os, sys; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('scripts/update_daily.py')))); from utils.elo import BASE_ELO, HOME_ADVANTAGE, K_BY_PHASE, update_elo; print('Import succeeded! BASE_ELO =', BASE_ELO)"
  ```
* **Verbatim Terminal Output:**
  ```text
  Import succeeded! BASE_ELO = 1500
  ```
  *(Exit code: `0`)*

---

### Observation 1.2: `encode_base_state` vs `RE24` Dictionary Keys
* **Target File & Lines:** `utils/wpa_engine.py:18-36`
* **Definition in code:**
  - Line 17: `# Base states: 0: ---, 1: 1--, 2: -2-, 3: --3, 4: 12-, 5: 1-3, 6: -23, 7: 123`
  - Lines 20-21: `(0, 3): 1.350, (0, 4): 1.373`
  - Lines 34-36: `return int(bool(on_1b)) * 1 + int(bool(on_2b)) * 2 + int(bool(on_3b)) * 4`
* **Verification Command:**
  ```powershell
  python -c "from utils.wpa_engine import RE24, encode_base_state; states = [('---', False, False, False, 0), ('1--', True, False, False, 1), ('-2-', False, True, False, 2), ('--3', False, False, True, 3), ('12-', True, True, False, 4), ('1-3', True, False, True, 5), ('-23', False, True, True, 6), ('123', True, True, True, 7)]; print('State  | Expected | Returned | Match | RE24(0out) exp | RE24(0out) act'); print('-'*65); [print(f'{s[0]:<6} | {s[4]:<8} | {encode_base_state(s[1],s[2],s[3]):<8} | {str(encode_base_state(s[1],s[2],s[3]) == s[4]):<5} | {RE24[(0, s[4])]:<14.3f} | {RE24[(0, encode_base_state(s[1],s[2],s[3]))]:<14.3f}') for s in states]"
  ```
* **Verbatim Terminal Output:**
  ```text
  State  | Expected | Returned | Match | RE24(0out) exp | RE24(0out) act
  -----------------------------------------------------------------
  ---    | 0        | 0        | True  | 0.461          | 0.461         
  1--    | 1        | 1        | True  | 0.831          | 0.831         
  -2-    | 2        | 2        | True  | 1.068          | 1.068         
  --3    | 3        | 4        | False | 1.350          | 1.373         
  12-    | 4        | 3        | False | 1.373          | 1.350         
  1-3    | 5        | 5        | True  | 1.640          | 1.640         
  -23    | 6        | 6        | True  | 1.880          | 1.880         
  123    | 7        | 7        | True  | 2.192          | 2.192         
  ```
* **Discovery on `format_base_state` (`utils/wpa_engine.py:39-48`):**
  Executing `format_base_state(3)` currently returns `'◇ ◆ ◆'` (1B and 2B occupied) instead of `'◆ ◇ ◇'` (3B occupied). When `encode_base_state` is updated to return `3` for `--3`, `format_base_state` must also be updated in tandem; otherwise, the WPA UI in `pages/4_📈_Análisis_WPA.py:164, 509, 581` will render inverted base graphics.

---

### Observation 1.3: Simpson's Paradox on `pages/2` Rate Statistics
* **Target File & Lines:** `pages/2_⚾_Estadisticas_Individuales.py:885, 898, 901`
* **Current Code:**
  ```python
  team_avg = batting_df['avg'].mean() if 'avg' in batting_df.columns else 0
  team_era = pitching_df['era'].mean() if 'era' in pitching_df.columns else 0
  team_whip = pitching_df['whip'].mean() if 'whip' in pitching_df.columns else 0
  ```
* **Verification Test Command:**
  ```powershell
  python -c "import pandas as pd; p = pd.DataFrame([{'ip': 60.0, 'er': 15, 'h': 45, 'bb': 15, 'era': 2.25, 'whip': 1.00}, {'ip': 25.0, 'er': 8, 'h': 20, 'bb': 8, 'era': 2.88, 'whip': 1.12}, {'ip': 0.1, 'er': 3, 'h': 3, 'bb': 1, 'era': 81.00, 'whip': 12.00}]); b = pd.DataFrame([{'ab': 200, 'h': 60, 'avg': 0.300}, {'ab': 180, 'h': 54, 'avg': 0.300}, {'ab': 1, 'h': 1, 'avg': 1.000}, {'ab': 2, 'h': 0, 'avg': 0.000}]); print(f'ERA .mean(): {p[\"era\"].mean():.2f} vs Real: {(p[\"er\"].sum()*9)/p[\"ip\"].sum():.2f}'); print(f'WHIP .mean(): {p[\"whip\"].mean():.2f} vs Real: {(p[\"h\"].sum()+p[\"bb\"].sum())/p[\"ip\"].sum():.2f}'); print(f'AVG .mean(): {b[\"avg\"].mean():.3f} vs Real: {b[\"h\"].sum()/b[\"ab\"].sum():.3f}')"
  ```
* **Verbatim Terminal Output:**
  ```text
  ERA .mean(): 28.71 vs Real: 2.75
  WHIP .mean(): 4.71 vs Real: 1.08
  AVG .mean(): 0.400 vs Real: 0.300
  ```

---

### Observation 1.4: Pythagorean Expectation $0/0$ Edge Case
* **Target File & Lines:** `pages/1_📊_Standings.py:494, 529`
* **Current Code:**
  ```python
  pyth_pct = (cf**1.83) / ((cf**1.83) + (cp**1.83))
  ...
  pyth_display['pyth_fmt'] = pyth_display['pyth_pct'].apply(lambda x: f".{int(x*1000):03d}")
  ```
* **Verification Test Command:**
  ```powershell
  python -c "import pandas as pd, numpy as np; cf = pd.Series([0.0]); cp = pd.Series([0.0]); pyth_pct = (cf**1.83) / ((cf**1.83) + (cp**1.83)); pyth_pct.apply(lambda x: f'.{int(x*1000):03d}')"
  ```
* **Verbatim Terminal Output:**
  ```text
  ValueError: cannot convert float NaN to integer
  ```

---

## 2. Logic Chain

1. **Import Resolution (Observation 1.1):** When running `python scripts/update_daily.py`, Python sets `sys.path[0]` to the directory containing the script (`scripts/`). Because `utils` is located at the project root (`./utils`), Python cannot find it and raises `ModuleNotFoundError`. Injecting `sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` adds the project root to `sys.path` dynamically, enabling reliable autonomous execution across local CLI, cron, and task runners without requiring manual environment variables.
2. **RE24 Mathematical Inversion (Observation 1.2):** Binary bitweight calculation ($1B \times 1 + 2B \times 2 + 3B \times 4$) maps `--3` (runner on 3B only) to integer `4` and `12-` (runners on 1B and 2B) to integer `3`. However, the `RE24` dictionary follows Tom Tango's standard indexation where key `3` is `--3` (1 runner) and key `4` is `12-` (2 runners). Consequently, run expectancies and WPA values are systematically swapped whenever these base configurations occur.
3. **Format Base State Coupling (Observation 1.2):** `format_base_state` in `utils/wpa_engine.py:39-48` relies on bitwise masks `& 1`, `& 2`, `& 4`. If `encode_base_state` is updated to output Tango indices (3 for `--3`, 4 for `12-`) without updating `format_base_state`, `format_base_state` will display `◇ ◆ ◆` for `--3` and `◆ ◇ ◇` for `12-`. Both functions must be updated in tandem.
4. **Simpson's Paradox (Observation 1.3):** Computing `.mean()` on pre-calculated rate statistics treats every individual equally regardless of innings pitched or at-bats. A single relief pitcher with 0.1 IP and 3 ER ($ERA=81.00$) inflates the team ERA from an elite $2.75$ to an abysmal $28.71$. Aggregating raw counts ($\sum ER \times 9 / \sum IP$, $\sum H / \sum AB$) is mathematically mandatory.
5. **Division by Zero in Standings (Observation 1.4):** When a team has 0 runs scored and 0 runs allowed ($CF=0, CP=0$), $0^{1.83} / (0^{1.83} + 0^{1.83}) = 0/0 = \text{NaN}$. Attempting to format `NaN` via `int(x * 1000)` causes an unhandled `ValueError`, crashing the Pythagorean tab for empty seasons or early-season views. Protecting the denominator with `np.where(denom > 0, ..., 0.500)` guarantees stability.

---

## 3. Caveats

* **Production Secrets:** Full end-to-end execution of `scripts/update_daily.py` connects to live Supabase and MLB Stats API and requires active `SUPABASE_URL` and `SUPABASE_KEY` credentials in the local environment. Our empirical verification tested the import phase and syntax resolution cleanly.
* **Format Base State:** This dependent bug was not highlighted in the original audit report `AUDIT_REPORT_REPUBLICA_CARAQUISTA.md`. The remediation team must fix both `encode_base_state` and `format_base_state` together.
* **No caveats regarding empirical validity:** All 4 reported bugs are 100% reproducible with deterministic proofs.

---

## 4. Conclusion

* **Explicit Verdict:** **`APPROVE`**
* **Assessment:** The findings presented in `AUDIT_REPORT_REPUBLICA_CARAQUISTA.md` are completely accurate, mathematically sound, and empirically verified under strict test harnesses.
* **Mandatory Action Items for Implementers:**
  1. Fix `scripts/update_daily.py` with `sys.path.append(...)`.
  2. Fix `encode_base_state` AND `format_base_state` in `utils/wpa_engine.py` using explicit dictionary mapping.
  3. Replace `.mean()` on `pages/2_⚾_Estadisticas_Individuales.py:885,898,901` with weighted sums.
  4. Safeguard `pyth_pct` and `pct_fmt` in `pages/1_📊_Standings.py:494,528,529` with `np.where`.

---

## 5. Verification Method

To independently reproduce all tests, run the following commands from `c:/Users/Administrator/Projets/RepubliCaraquistApp`:

```powershell
# 1. Verify update_daily.py failure & fix:
python scripts/update_daily.py
python -c "import os, sys; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('scripts/update_daily.py')))); from utils.elo import BASE_ELO; print('Fix works! BASE_ELO =', BASE_ELO)"

# 2. Verify RE24 encoding inversion & format_base_state bug:
python -c "from utils.wpa_engine import RE24, encode_base_state, format_base_state; print('--3 got:', encode_base_state(False,False,True), 'expected: 3'); print('12- got:', encode_base_state(True,True,False), 'expected: 4'); print('format_base_state(3):', format_base_state(3))"

# 3. Verify Simpson's paradox:
python -c "import pandas as pd; df = pd.DataFrame([{'ip': 60.0, 'er': 15, 'era': 2.25}, {'ip': 0.1, 'er': 3, 'era': 81.00}]); print('Mean ERA:', df['era'].mean(), '| Weighted:', (df['er'].sum()*9)/df['ip'].sum())"

# 4. Verify Pythagorean NaN crash & fix:
python -c "import pandas as pd, numpy as np; cf = pd.Series([0.0]); cp = pd.Series([0.0]); denom = cf**1.83 + cp**1.83; print('Fixed:', pd.Series(np.where(denom > 0, cf**1.83/denom, 0.500)).apply(lambda x: f'.{int(x*1000):03d}')[0])"
```
