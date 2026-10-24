# Comprehensive Technical Audit: UK Wind Generation Forecast Accuracy Dashboard

**Audited System:** UK Wind Generation Forecast Accuracy Terminal  
**Primary Data Source:** Elexon BMRS Open API v1 (`FUELHH` & `WINDFOR`)  
**Evaluation Scope:** Codebase inspection, auction cutoff verification, Elexon endpoint semantics, vintage history causality, resolution alignment, metric consistency, regression testing, and build verification.

---

## 1. Executive Summary & Audit Scope

This technical audit reviews the data engineering architecture, electricity market domain assumptions, and forecast evaluation methodology of the UK Wind Generation Forecast Accuracy Terminal. The audit identified, corrected, and verified the following critical data and market engineering elements:

1. **Resolution of the Day-Ahead Auction Cutoff:**
   - Previous reviews cited conflicting cutoff times, including an unverified 11:00 UK assumption and references to N2EX timings.
   - Authoritative investigation of current GB power exchange documentation confirms that order books for the two primary GB Day-Ahead physical auctions close at:
     - **EPEX SPOT GB Day-Ahead 60 Auction:** **09:20 London Local Time (GMT/BST)** on $D-1$ (results published from 09:30).
     - **Nord Pool / N2EX GB Day-Ahead Auction:** **09:50 London Local Time (GMT/BST)** on $D-1$ (results published at 10:00 London time / 11:00 CET).
     - **EPEX SPOT GB Half-Hour Day-Ahead Auction:** **15:30 London Local Time (GMT/BST)** on $D-1$.
     - **NESO Indicative Day-Ahead Schedule:** Published at **17:00 London Local Time (GMT/BST)** on $D-1$.
     - **Balancing Mechanism (BM) Gate Closure:** Exactly **1 hour prior** to each half-hour delivery interval.
   - *Origin of Legacy 11:00 Citation:* Conflation of European Single Day-Ahead Coupling (SDAC 12:00 CET / 11:00 UK time, which GB exited post-Brexit) or N2EX Continental European results timing (11:00 CET = 10:00 UK time).
   - *Implementation:* The system now provides verified venue presets with EPEX SPOT (09:20 London time) as the primary default for the standard hourly physical delivery contract, with timezone transitions handled dynamically via `Europe/London`.

2. **Verification of Elexon WINDFOR Historical-Vintage Semantics:**
   - Raw records and official documentation from `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream` were inspected.
   - National Grid ESO produces continuous 74-hour forecast trajectory runs (~10 runs per day). Each run includes ~21 hours of backward-looking numerical weather prediction (NWP) assimilation tail (`startTime <= publishTime`) and ~53 hours of forward forecast (`startTime > publishTime`).
   - Forecast records published after delivery time are the assimilation initial conditions of subsequent model runs, NOT post-delivery forecast revisions.
   - To prevent look-ahead leakage, retrospective pre-delivery evaluation strictly enforces $\text{publish\_time} \le \text{delivery\_time}$.

3. **Elimination of Stale and Inconsistent Accuracy Figures:**
   - All superseded figures (e.g. MAE of ~2,091–2,093 MW) from obsolete, unconstrained `MAX(publish_time)` queries have been removed from the primary benchmarks.
   - A single, canonical set of reproduced metrics across all evaluation modes is established as the sole source of truth.

4. **Preservation of the 4 Missing Pairs Mathematical Explanation:**
   - In the fixed snapshot evaluation as of `2025-12-31T11:30:00Z`, 46 of 120 hours (92 of 240 half-hours) were valid, leaving 74 missing hours (148 half-hours).
   - The National Grid forecast run published at Dec 31 11:30 UTC spanned exactly 74 hours to Jan 2 21:00 UTC. The final two hours of Jan 2 (`22:00:00Z` and `23:00:00Z`) had not yet been published (they arrived in the 12:00 UTC run). In half-hourly settlement periods, those 2 hours equal **exactly 4 settlement periods** (SP 45, 46, 47, 48). Thus, $48 + 44 = 92$ valid half-hourly pairs.

---

## 2. Auction Venues, Products & Market Cutoff Rules

In the GB electricity market, market participants trade day-ahead contracts across distinct exchanges and regulatory schedules. These events do not share a universal deadline:

| Market Event / Venue | Product / Document Citation | Authoritative Rule | Summer / Winter UTC |
| :--- | :--- | :--- | :--- |
| **EPEX SPOT GB Day-Ahead 60** | *EPEX SPOT Operational Rules & GB Trading Brochure* (Effective Jan 2021 post-Brexit SDAC decoupling) | **09:20 London Local Time** on $D-1$ (Results unblinded & published ~09:30) | 09:20 UTC (GMT) / 08:20 UTC (BST) |
| **Nord Pool / N2EX GB Day-Ahead** | *Nord Pool Trading Rules – Appendix 1 (Auction Rules – GB Day-Ahead)*, Section 2.1 | **09:50 London Local Time** on $D-1$ (Results published by 10:00 London / 11:00 CET) | 09:50 UTC (GMT) / 08:50 UTC (BST) |
| **EPEX SPOT GB Day-Ahead 30** | *EPEX SPOT Operational Rules (GB 30-Minute Auction)* | **15:30 London Local Time** on $D-1$ | 15:30 UTC (GMT) / 14:30 UTC (BST) |
| **NESO Day-Ahead Schedule** | *GB Grid Code – Operating Code No. 1 (OC1: Demand Forecasts)* & *Balancing Code No. 1 (BC1)*, Section BC1.4.1 | **17:00 London Local Time** on $D-1$ (Programming Phase closure) | 17:00 UTC (GMT) / 16:00 UTC (BST) |
| **Balancing Mechanism Gate Closure** | *Balancing and Settlement Code (BSC) Section P*, Section 1.2 & *Grid Code BC1.4.2* | **$T_{\text{delivery}} - 60 \text{ min}$** (1 hour prior to settlement start) | Dynamic per 30-min settlement period |

### Authoritative Venue Document Citations & Context
1. **EPEX SPOT SE:** *Trading System Specifications & Operational Procedures – Great Britain Day-Ahead Auctions*. The 09:20 GMT/BST order-book closure for the GB Day-Ahead 60 Auction was established when Great Britain exited the EU Internal Energy Market and European Single Day-Ahead Coupling (SDAC). The 09:20 timing allows participants to submit local bids following interconnector capacity allocation.
2. **Nord Pool European Market Coupling Operator AS:** *N2EX Day-Ahead Auction Product Specification*. Specifies order submission deadline at **09:50 GMT/BST** (10:50 CET/CEST) with market clearing results released by 10:00 GMT (11:00 CET).
3. **National Energy System Operator (NESO):** *The Grid Code (Issue 6, Revision 14)*, *Operating Code 1 (OC1.5.5)* and *Balancing Code 1 (BC1.4.1)*. Defines the **Programming Phase** deadline at **17:00 hours on the day preceding the operational day**, at which point NESO finalizes day-ahead operational planning and publishes indicated demand and generation profiles.
4. **Elexon Limited:** *Balancing and Settlement Code (BSC) Section P (Energy Contract Volumes and Metered Volume Reallocations)*, paragraph 1.2. Defines **Gate Closure** as precisely one hour prior to the start of each Half Hour delivery interval, prohibiting further bilateral contract notifications or physical notification adjustments.

### Timezone Conversion Mechanics
The application uses Python's standard `zoneinfo.ZoneInfo("Europe/London")` to compute the UTC cutoff for any delivery date:
```python
def get_day_ahead_cutoff_utc(delivery_date: str, cutoff_time_str: str = "09:20") -> datetime:
    d = date.fromisoformat(delivery_date)
    d_prev = d - timedelta(days=1)
    hh, mm = [int(x) for x in cutoff_time_str.split(":")]
    dt_local = datetime(d_prev.year, d_prev.month, d_prev.day, hh, mm, 0, tzinfo=ZoneInfo("Europe/London"))
    return dt_local.astimezone(timezone.utc)
```
- During **GMT (Winter)**: 09:20 London time evaluates to `09:20:00Z`.
- During **BST (Summer)**: 09:20 London time evaluates to `08:20:00Z`.


---

## 3. Elexon WINDFOR Historical-Vintage Semantics

The Elexon BMRS Open API v1 endpoint `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream` delivers the official wind generation forecast published by the National Energy System Operator (NESO).

### Verified Endpoint Semantics
1. **`publishTime`**: The exact UTC timestamp at which NESO published the model trajectory run.
2. **`startTime`**: The start time of the 1-hour forecast delivery interval (always ending in `:00:00Z`).
3. **Forecast Horizon & Run Structure**:
   - Each publication run contains a continuous 74-hour trajectory vector.
   - Runs are published approximately 10 times daily (typically at 00:00, 02:30, 04:30, 06:00, 07:30, 09:30, 11:30, 15:30, 17:30, 21:30 UTC).
4. **Post-Delivery Records (Assimilation Tails)**:
   - For a run published at time $P$, records exist where $\text{startTime} \le P$ (covering approximately 21 hours prior to publication) and $\text{startTime} > P$ (covering approximately 53 hours forward).
   - Records with $\text{startTime} \le P$ are the NWP data assimilation / hindcast state of that specific model run.
   - Consequently, finding a record with `publish_time > delivery_time` does **not** signify an ex-post revision to a previously traded forecast; it is the hindcast portion of a subsequent run.
5. **Point-in-Time Eligibility Rules**:
   - **Rolling Day-Ahead Evaluation**: For each delivery date $D$, select the latest vintage with:
     $$\text{publish\_time} \le \text{Cutoff}_{\text{venue}}(D-1)$$
   - **Retrospective Latest Pre-Delivery Evaluation**: For each delivery interval, select the latest vintage with:
     $$\text{publish\_time} \le \text{delivery\_time}$$
   - **Deterministic Tie-Breaking**: Broken deterministically by `(publish_time DESC, id DESC, retrieval_time DESC)`.

---

## 4. Resolution Alignment & Energy Volume Accounting

### Primary Methodology: Hourly Native 1-to-1
National Grid publishes `WINDFOR` at 1-hour resolution, while `FUELHH` reports metered outturn in 30-minute settlement periods. The primary evaluation methodology aggregates outturn to hourly resolution:
$$A_{\text{hour}} = \frac{A_{\text{SP}_{2k-1}} + A_{\text{SP}_{2k}}}{2}$$
- **Completeness Invariant**: Both constituent half-hours ($A_{\text{SP}_{2k-1}}$ and $A_{\text{SP}_{2k}}$) must be present. If either half-hour is missing, the hourly actual is set to `None` to prevent distortion.
- **Statistical Integrity**: Preserves native independent forecast points ($N=120$ for 5 days) without introducing intra-hour ramp artifacts.

### Secondary Methodology: Half-Hourly Broadcast
In half-hourly broadcast mode, the hourly forecast value is repeated across both settlement periods:
$$F_{\text{SP}_{2k-1}} = F_{\text{hour}}, \quad F_{\text{SP}_{2k}} = F_{\text{hour}}$$
- **Limitations**: Broadcasting does **not** double the independent forecast information. Intra-hour wind ramping naturally creates divergence between the flat forecast block and the two 30-minute actuals, resulting in slightly higher MAE and RMSE.

### Energy Volume Formulation (MWh)
Energy volume must strictly incorporate interval duration $\Delta t$:
$$\text{MWh} = \sum_{t=1}^N P_t \times \Delta t$$
- For **Hourly Evaluation**: $\Delta t = 1.0\text{ hour}$
- For **Half-Hourly Evaluation**: $\Delta t = 0.5\text{ hour}$

---

## 5. Canonical Jan 1–5, 2026 Reproduction & Benchmark Truth

The following table presents the canonical, reproducible benchmark figures calculated directly from the verified stored SQLite dataset (240 FUELHH records, 3,136 WINDFOR records):

| Evaluation Mode | Venue / Cutoff Rule | Alignment | Valid / Expected | Coverage | Bias (ME) | MAE | RMSE | WAPE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rolling Day-Ahead** | **EPEX SPOT GB 60 (D-1 09:20 London)** | Hourly Native | 120 / 120 | 100.0% | **-2,090.60 MW** | **2,429.28 MW** | **3,029.48 MW** | **17.70%** |
| **Rolling Day-Ahead** | **EPEX SPOT GB 60 (D-1 09:20 London)** | Half-Hour Broadcast | 240 / 240 | 100.0% | **-2,090.60 MW** | **2,430.07 MW** | **3,033.86 MW** | **17.70%** |
| **Rolling Day-Ahead** | **Nord Pool GB (D-1 09:50 London)** | Hourly Native | 120 / 120 | 100.0% | **-2,079.43 MW** | **2,346.83 MW** | **3,000.66 MW** | **17.10%** |
| **Rolling Day-Ahead** | **Nord Pool GB (D-1 09:50 London)** | Half-Hour Broadcast | 240 / 240 | 100.0% | **-2,079.43 MW** | **2,349.11 MW** | **3,005.09 MW** | **17.11%** |
| **Rolling Day-Ahead** | **Legacy Reference (D-1 11:00 London)** | Hourly Native | 120 / 120 | 100.0% | **-2,079.43 MW** | **2,346.83 MW** | **3,000.66 MW** | **17.10%** |
| **Rolling Day-Ahead** | **NESO Schedule (D-1 17:00 London)** | Hourly Native | 120 / 120 | 100.0% | **-2,362.66 MW** | **2,461.78 MW** | **3,123.58 MW** | **17.93%** |
| **Retrospective** | **Latest Pre-Delivery ($P \le T_{\text{del}}$)** | Hourly Native | 120 / 120 | 100.0% | **-1,534.86 MW** | **2,413.43 MW** | **3,096.52 MW** | **17.58%** |
| **Retrospective** | **Latest Pre-Delivery ($P \le T_{\text{del}}$)** | Half-Hour Broadcast | 240 / 240 | 100.0% | **-1,534.86 MW** | **2,420.44 MW** | **3,100.81 MW** | **17.63%** |
| **Fixed Snapshot** | **Dec 31, 2025, 11:30 UTC** | Hourly Native | 46 / 120 | 38.33% | **-486.54 MW** | **930.46 MW** | **1,175.20 MW** | **5.69%** |
| **Fixed Snapshot** | **Dec 31, 2025, 11:30 UTC** | Half-Hour Broadcast | 92 / 240 | 38.33% | **-486.54 MW** | **933.61 MW** | **1,179.94 MW** | **5.71%** |

### Reconciliation with Historical Figures
- **Obsolete Unrestricted Figures (~2,091–2,093 MW MAE):** These numbers were the result of the unconstrained `MAX(publish_time)` query bug that inadvertently selected ex-post assimilation tails published up to 5 days after delivery. They are now superseded.
- **EPEX SPOT (09:20) vs. Nord Pool (09:50):** National Grid published a new model run at 09:30 UTC on D-1. Consequently, EPEX SPOT orders (closed at 09:20) captured the 07:30 UTC run (MAE 2,429.28 MW), whereas Nord Pool orders (closed at 09:50) captured the newer 09:30 UTC run (MAE 2,346.83 MW).
- **Snapshot Coverage (38.33%):** Dec 31 11:30 UTC forecast horizon ended at Jan 2 21:00 UTC. The final 2 hours of Jan 2 (4 SPs) and all of Jan 3–5 (72 hours / 144 SPs) had not yet been published, explaining the exactly 46 valid hours (92 half-hours).

---

## 6. Error Convention & Economic Interpretation

### Error Convention
In accordance with GB electricity market convention:
$$e_t = A_t - F_t$$
- **Positive Bias ($e_t > 0$):** Actual generation exceeded forecast (**underforecasting**; physical system in volume surplus).
- **Negative Bias ($e_t < 0$):** Forecast exceeded actual generation (**overforecasting**; physical system in volume deficit).

### Non-Inference of Trading Profitability
The observed negative bias across Jan 1–5, 2026 (mean error of approximately $-2,080$ to $-2,090$ MW) indicates systematic overforecasting during this winter storm period. 
> **Important Market Distinction:** A negative forecast bias does **not** directly indicate trading losses or gains. In the GB market, cashout exposure is governed by the Dual/Single Imbalance Price mechanism (System Buy Price / System Sell Price) and the participant's net contract position relative to the overall system imbalance direction (NIV). Forecast error metrics evaluate meteorological skill and model quality; financial impact requires portfolio imbalance cashout simulation.

---

## 7. Automated Test Verification

The codebase includes deterministic regression test suites that run independently of external API network availability:

### Backend Test Suite (`python -m pytest backend/tests -v`)
**Result: 35 passed in 3.57s (100% pass rate)**
- `test_audit_requirements.py`:
  - `test_api_chunking_boundaries`: Verifies 6-day chunking adhering to Elexon $\le 7$ day HTTP 400 constraint.
  - `test_duplicate_ingestion_across_boundaries`: Tests upsert idempotency across query windows.
  - `test_dst_clock_change_settlement_counts`: Validates 46, 48, and 50 settlement periods for clock change days.
  - `test_missing_data_provenance_and_zero_actual`: Verifies WAPE zero-division safety and status provenance.
  - `test_auction_venue_cutoff_conversions`: Tests EPEX (09:20), Nord Pool (09:50), and NESO (17:00) cutoffs across GMT and BST.
  - `test_canonical_reproducibility_from_stored_db`: Confirms 100% exact numerical reproduction of Jan 1–5 canonical metrics across all 5 evaluation modes (EPEX 09:20, Nord Pool 09:50, NESO 17:00, retrospective, snapshot).
  - `test_metric_formula_falsifiability`: Directly proves mathematical sensitivity and falsifiability (proves that inverted error conventions, altered differences, or wrong denominators fail).
- `test_alignment.py`:
  - Tests half-hourly broadcast alignment.
  - Tests hourly averaging ($A_{\text{hour}} = (A_1 + A_2)/2$).
  - Tests that incomplete hours (where one SP is missing) return `None` rather than halved generation.
- `test_metrics.py`:
  - Hand-verified MAE, RMSE, Bias, and WAPE calculations.
  - WAPE handling with zero actuals.
  - Energy volume duration weighting ($\text{MWh} = \text{MW} \times \Delta t$).
- `test_vintage_selector.py`:
  - Strict cutoff filtering and deterministic tie-breaking.
  - Rejection of post-delivery records in retrospective evaluation.
  - Multi-day rolling day-ahead cutoff evaluation.
  - British Summer Time (BST) offset calculation.
  - `test_later_published_hindcast_cannot_replace_eligible_forecast`: Regression test explicitly proving that later-published NWP assimilation tails or hindcasts cannot replace an eligible forecast for either Day-Ahead or retrospective evaluations.

### Frontend Test Suite (`npm test -- --run`)
**Result: 7 passed in 5.66s (100% pass rate)**
- Component testing verifying venue presets (09:20, 09:50, 15:30, 17:00), cutoff selection, status badges, and API query generation.

### Production Bundle Build (`npm run build`)
**Result: Successful compilation with 0 TypeScript errors in 7.23s.**
- Output: `dist/assets/index-BgeUgxxR.js` (620 kB) and `dist/assets/index-DdYMB6KH.css` (4.72 kB).


---

## 8. Deployment Status & Limitations

- **Live Development Servers:**
  - Backend API: Active on `http://127.0.0.1:8000` (FastAPI / Uvicorn).
  - Frontend Application: Active on `http://localhost:5173` (Vite dev server).
- **Docker Verification Status:**
  - The local development host does not have the Docker daemon / CLI installed in `PATH`.
  - In accordance with the audit mandate, **Docker runtime execution remains unverified on this host**.
  - Dockerfile and `docker-compose.yml` configurations have been inspected and validated for static correctness.
