# UK Wind Generation Forecast Accuracy Terminal

A production-grade analytics and decision-support terminal built for UK electricity traders evaluating National Grid / NESO wind generation forecasts (`WINDFOR`) against Elexon outturn metered actuals (`FUELHH`) to support Day-Ahead power purchasing decisions.

---

## 1. Project Overview & Business Value

In the Great Britain (GB) electricity market, day-ahead power contracts clear at fixed auction gate closures (e.g., EPEX SPOT and Nord Pool at 11:00 UTC / 12:00 London time, D-1). Electricity traders must commit to purchase or sell volume before real-time delivery begins. Wind power is the primary source of volume volatility and price cannibalization in GB.

This dashboard answers core trading questions:
1. **Latest Eligible Forecast:** What was the most recently published wind forecast prior to a selected decision cutoff (e.g., Day-Ahead Auction Gate Closure)?
2. **Convergence & Evolution:** How did the wind forecast evolve across historical publication runs as delivery approached?
3. **Accuracy & Directional Bias:** Did the forecast consistently underpredict (system short, positive bias) or overpredict (system long, negative bias) actual wind generation?
4. **Tail Risk:** How extreme were the forecast misses (measured by Root Mean Squared Error, RMSE)?
5. **Data Completeness & Auditability:** What delivery intervals have missing forecasts, missing settlement meter data, or daylight-saving anomalies?

> **Trading Notice:** This application is strictly analytical and read-only. Forecast accuracy metrics alone do not guarantee trading profit or eliminate financial risk. No trade execution or portfolio ordering is performed.

---

## 2. Key Features

- **Strict Historical Decision-Cutoff Engine:** Evaluates forecasts at point-in-time boundaries (e.g., Day-Ahead 11:00 UTC, 17:00 UTC, or custom UTC timestamps). Completely eliminates look-ahead bias and future data leakage.
- **Publication Vintage Audit:** For every half-hourly or hourly delivery interval, tracks all revision runs published by National Grid / NESO, with exact publication timestamps, lead times, and eligibility markers.
- **UK Market Settlement Alignment:** Aligns half-hourly `FUELHH` metered generation (Settlement Periods 1–48) with hourly `WINDFOR` forecasts, supporting both half-hourly settlement intervals and hourly aggregations.
- **Daylight-Saving Time Precision:** Handles clock-change transitions mathematically using Python `zoneinfo` (`Europe/London`):
  - Normal Day: 48 settlement periods (24 hours)
  - Spring Clock-Forward: 46 settlement periods (23 hours)
  - Autumn Clock-Back: 50 settlement periods (25 hours)
- **Mathematical Error Metrics:**
  - **Mean Absolute Error (MAE):** Linear average miss magnitude in MW.
  - **Root Mean Squared Error (RMSE):** Quadratic miss penalty highlighting extreme tail dispatch risk in MW.
  - **Mean Error / Bias (ME):** Directional balance: positive indicates generation exceeded forecast (underforecast), negative indicates generation fell short (overforecast).
  - **Weighted Absolute Percentage Error (WAPE):** Mathematically robust percentage error avoiding zero-division singularities of standard MAPE.
  - **Paired Coverage (%):** Percentage of expected delivery intervals with valid forecast and actual pairs.
- **Antigravity Glassmorphism UI:** Built following the `antigravity-design-expert` workflow: dark carbon surfaces (`#080C14`), glassmorphism backdrop blur (`rgba(17, 25, 40, 0.75)`), cyan forecast lines, emerald actual lines, tabular numeric typography (`font-variant-numeric: tabular-nums`), responsive charts, and custom tooltips.
- **Dual Operating Modes:**
  - **Live Market Mode:** Queries the official Elexon BMRS API (`https://data.elexon.co.uk/bmrs/api/v1`) with bounded retries, rate limiting, and SQLite caching.
  - **Deterministic Demo Mode:** Complete offline fixture dataset covering January 1–3, 2026 for automated testing and isolated demonstrations.
- **Identical Methodology CSV Export:** One-click CSV export matching on-screen formulas with explicit null handling (never silently coerced to zero).

---

## 3. Screens & Visual Workflow

The frontend comprises four dedicated screens accessible via top-level tab navigation:

### Screen A: Trading Overview
- Top trading snapshot cards: Latest eligible forecast (WINDFOR MW), latest available actual (FUELHH MW), and active decision-cutoff status.
- Executive KPI deck: MAE, RMSE, Bias (ME), WAPE, Coverage, and Total Energy (GWh).
- Interactive time-series profile chart with actual generation (emerald gradient area and solid line) and selected forecast (dashed cyan line).
- Period analytical narrative summarizing accuracy and directional bias for the selected evaluation window.

### Screen B: Forecast Accuracy
- Time series profile with interactive point selection.
- Error-over-time deviation bar chart ($e_t = A_t - F_t$) colored emerald for underforecasting (+) and rose for overforecasting (-).
- Daily aggregation table: Day-by-day MAE, RMSE, bias, WAPE, and coverage.
- Granular settlement interval table with search, status filtering (Valid, Missing Forecast, Missing Actual), pagination, and vintage audit links.
- Trader guidance panel explaining metric interpretation and risk implications.

### Screen C: Forecast History & Vintages
- Delivery interval picker allowing the trader to choose any target delivery timestamp.
- Revision-over-time evolution chart tracking forecast values across publication runs as lead time diminished.
- Reference line marking the actual outturn generation.
- Detailed publication audit table showing publication timestamp (UTC and London), lead time in hours, MW revision from prior run, cutoff eligibility, and active decision vintage.

### Screen D: Data Status & Cache Health
- Real-time Elexon BMRS API connectivity check and ping latency (ms).
- SQLite database status: Total cached records, forecast count, actuals count, and cached date ranges.
- Dataset specifications: Documented endpoints, parameters, and fields for `FUELHH` and `WINDFOR`.
- On-demand ingestion tool: Fetch and cache any date range directly from Elexon API.

---

## 4. Architecture & Data Flow

```
                      +---------------------------------------+
                      |           Elexon BMRS API             |
                      |   https://data.elexon.co.uk/bmrs/api  |
                      +-------------------+-------------------+
                                          |
                        HTTP GET (<= 7-day chunked queries)
                                          v
+-----------------------------------------------------------------------------------+
|                                FastAPI Backend                                    |
|                                                                                   |
|  +---------------------+      +---------------------+      +-------------------+  |
|  |    Elexon Client    | ---> | SQLite Persistence  | ---> | Vintage Selector  |  |
|  |  (Chunking & Retry) |      | (WAL Mode, Dedupe)  |      | (Cutoff & Leaks)  |  |
|  +---------------------+      +---------------------+      +-------------------+  |
|                                                                      |            |
|  +---------------------+      +---------------------+                |            |
|  | Accuracy Metrics &  | <--- | Interval Alignment  | <--------------+            |
|  | CSV Export Service  |      | (Half-Hour/Hourly)  |                             |
|  +---------------------+      +---------------------+                             |
+------------------------------------------+----------------------------------------+
                                           |
                                  JSON REST API / CSV
                                           v
+-----------------------------------------------------------------------------------+
|                                React Frontend (Vite)                              |
|                                                                                   |
|   Header (Live API Status / Mode Toggle) & Navigation                             |
|   Trading Controls (Date Range, Decision Cutoff, Granularity)                      |
|                                                                                   |
|   +-------------------+  +-------------------+  +-------------------+  +--------+ |
|   | Screen A: Overview|  | Screen B: Accuracy|  | Screen C: Vintages|  |Screen D| |
|   | (KPIs & Profile)  |  | (Error Dev & Table|  | (Revision Chart)  |  |(Status)| |
|   +-------------------+  +-------------------+  +-------------------+  +--------+ |
|                                                                                   |
|   Antigravity Design System (Vanilla CSS, Glassmorphism, Tabular Mono, Recharts)  |
+-----------------------------------------------------------------------------------+
```

---

## 5. Official Elexon Datasets & Verified API Specs

Our implementation queries official Elexon BMRS REST API endpoints:
- **Base URL:** `https://data.elexon.co.uk/bmrs/api/v1`
- **Documentation:** [Elexon BMRS Documentation](https://bmrs.elexon.co.uk/api-documentation)

### 1. Actual Generation: `FUELHH`
- **Endpoint:** `/datasets/FUELHH`
- **Query Parameters Verified:**
  - `settlementDateFrom` (YYYY-MM-DD)
  - `settlementDateTo` (YYYY-MM-DD)
  - `fuelType=WIND`
- **Query Constraint:** Elexon strictly enforces that the date range between `settlementDateFrom` and `settlementDateTo` inclusive must not exceed **7 days**. The backend automatically chunks date ranges into 6-day slices.
- **Response Structure Verified:**
  ```json
  {
    "dataset": "FUELHH",
    "publishTime": "2026-01-02T00:00:00Z",
    "startTime": "2026-01-01T23:30:00Z",
    "settlementDate": "2026-01-01",
    "settlementPeriod": 48,
    "fuelType": "WIND",
    "generation": 15538
  }
  ```

### 2. Wind Generation Forecast: `WINDFOR`
- **Endpoint:** `/datasets/WINDFOR`
- **Query Parameters Verified:**
  - `publishDateTimeFrom` (ISO 8601 UTC)
  - `publishDateTimeTo` (ISO 8601 UTC)
- **Query Constraint:** Range between `publishDateTimeFrom` and `publishDateTimeTo` must not exceed **7 days**.
- **Historical Vintage Preservation:** Each publication run contains hourly forecast values (`startTime`) for up to 72 hours into the future. Each run retains its distinct `publishTime`.
- **Response Structure Verified:**
  ```json
  {
    "dataset": "WINDFOR",
    "publishTime": "2025-12-31T11:30:00Z",
    "startTime": "2026-01-01T12:00:00Z",
    "generation": 19725
  }
  ```

---

## 6. Decision-Cutoff & Vintage Selection Semantics

### The Core Problem: Look-Ahead Bias
If a dashboard simply selects today's latest forecast for a historical delivery date, it commits **look-ahead leakage**. A day-ahead trader at 11:00 UTC on D-1 did not have access to forecasts published at 18:00 UTC on D-1 or intraday runs on D-0.

### Selection Rule
For any delivery interval with start time $T_{\text{delivery}}$, and a user-selected decision cutoff timestamp $T_{\text{cutoff}}$:
1. Identify all forecast records in the database with `delivery_time` == $T_{\text{delivery}}$.
2. Filter the candidate records:
   $$\text{Eligible} = \{ r \in \text{Vintages} \mid r.\text{publish\_time} \le T_{\text{cutoff}} \}$$
3. Select the eligible record with maximum `publish_time`:
   $$r^* = \arg\max_{r \in \text{Eligible}} (r.\text{publish\_time})$$
4. **Deterministic Tie-Break:** If multiple records have identical publication timestamps:
   - Rank by `id` descending (latest database insertion).
   - Rank by `retrieval_time` descending.
5. **No Look-Ahead Rule:** If $\text{Eligible}$ is empty, the forecast is marked unavailable (`None`). Missing forecasts are never silently replaced with later runs.

---

## 7. Mathematical Formulations & Units

Let $A_t$ be the actual metered generation (MW) from `FUELHH`, and $F_t$ be the selected forecast generation (MW) from `WINDFOR` for delivery interval $t$.
Error deviation is defined as:
$$e_t = A_t - F_t$$
For $N$ valid paired intervals:

| Metric | Formula | Units | Interpretation |
| :--- | :--- | :--- | :--- |
| **Mean Error (Bias / ME)** | $\frac{1}{N}\sum_{t=1}^{N}(A_t - F_t)$ | MW | $+ME$: Actual > Forecast (Underforecasting)<br>$-ME$: Actual < Forecast (Overforecasting) |
| **Mean Absolute Error (MAE)** | $\frac{1}{N}\sum_{t=1}^{N}\|A_t - F_t\|$ | MW | Average magnitude of forecast miss |
| **Root Mean Squared Error (RMSE)**| $\sqrt{\frac{1}{N}\sum_{t=1}^{N}(A_t - F_t)^2}$ | MW | Quadratic penalty emphasizing large tail risks |
| **Weighted Abs % Error (WAPE)** | $\frac{\sum_{t=1}^{N}\|A_t - F_t\|}{\sum_{t=1}^{N}\|A_t\|} \times 100\%$ | % | Volume-weighted error; robust against zero generation |
| **Coverage** | $\frac{N}{\text{Expected Intervals}} \times 100\%$ | % | Completeness of paired settlement intervals |

*Note: Standard MAPE is not used because actual wind generation in low-wind periods reaches zero or near zero, which causes undefined divisions by zero.*

---

## 8. Timezone & Settlement Interval Handling

- **Internal Storage & Joins:** All timestamps are stored and joined strictly in **UTC ISO 8601** format (`YYYY-MM-DDTHH:MM:SSZ`).
- **Display:** Formatted in local UK time (`Europe/London`) with explicit timezone abbreviations (`GMT` in winter, `BST` in summer).
- **Daylight-Saving Variations:**
  - Standard UK Day: 48 Settlement Periods (24h)
  - Spring Clock Change (e.g. 29 March 2026): 46 Settlement Periods (23h)
  - Autumn Clock Change (e.g. 25 October 2026): 50 Settlement Periods (25h)
- Ambiguous autumn fallback hours are resolved cleanly without duplicate timestamp clashes because UTC monotonically advances regardless of local clock adjustments.

---

## 9. Prerequisites & Local Execution

### Prerequisites
- Python 3.11+
- Node.js 18+ (tested on Node v26)
- Docker & Docker Compose (optional, for containerized run)

### Running Locally without Docker

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run backend automated tests
pytest tests -v

# Start FastAPI backend server (runs on port 8000)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup
```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Install node dependencies
npm install

# Run frontend tests
npm test

# Build production bundle
npm run build

# Start Vite dev server (runs on port 5173 with proxy to port 8000)
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 10. Running with Docker Compose

To run the complete production stack (FastAPI backend + NGINX React frontend + persistent SQLite volume):

```bash
# Build and start services
docker compose up --build

# Shutdown services and preserve volume
docker compose down

# Shutdown and remove volumes
docker compose down -v
```

The frontend will be available at `http://localhost:3000` (or `http://localhost:80` inside container) and the backend API at `http://localhost:8000`.

---

## 11. Automated Testing Suite

### Backend Test Coverage (`pytest tests -v`)
All 22 unit and integration tests pass:
- `test_time_utils.py`: UTC conversions, London GMT/BST display, standard and DST settlement period generation (46, 48, 50 periods).
- `test_vintage_selector.py`: Decision-cutoff enforcement, prevention of look-ahead leakage, deterministic tie-breaking, evolution audit.
- `test_metrics.py`: Hand-verified calculations of MAE, RMSE, Bias, WAPE, zero-denominator handling, missing values, daily breakdown.
- `test_alignment.py`: Half-hourly settlement period pairing and hourly aggregation averaging.
- `test_database.py`: SQLite schema, deduplication on upsert, and cache statistics.
- `test_api.py`: FastAPI test client verifying `/health`, `/config/options`, `/evaluation`, `/vintages`, and `/export`.

### Frontend Test Coverage (`npm test`)
All 7 component tests pass using Vitest and Testing Library:
- `MetricKpiCard.test.tsx`: Renders all cards with correct units; handles nulls gracefully.
- `AlertBanner.test.tsx`: Renders quality warning banners; handles empty flags.
- `GranularDataTable.test.tsx`: Displays intervals, status badges, and triggers audit callbacks.
- `TradingControls.test.tsx`: Updates dates, triggers recalculation, and cutoff presets.
- `API.test.tsx`: Verifies CSV export URL parameter generation.

---

## 12. Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_PATH` | `data/wind_forecast.db` | Path to SQLite database file |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Official Elexon BMRS endpoint |
| `ELEXON_TIMEOUT_SECONDS` | `20.0` | HTTP request timeout in seconds |
| `ELEXON_MAX_RETRIES` | `3` | Bounded retries for 429/5xx responses |
| `DEFAULT_DATE_FROM` | `2026-01-01` | Default evaluation start date |
| `DEFAULT_DATE_TO` | `2026-01-31` | Default evaluation end date |
| `ALLOW_FIXTURE_FALLBACK`| `true` | Allows deterministic fixture fallback if live API is down |

---

## 13. Deployment Considerations

- **Persistent Storage:** SQLite requires persistent storage (e.g., Docker persistent volume, AWS EBS, or Fly.io volume). For serverless platforms (e.g. AWS Lambda, Vercel), SQLite will not persist across cold starts; a managed SQL database (PostgreSQL/TimescaleDB) or external object store should be configured.
- **CORS:** FastAPI CORS middleware is preconfigured to accept requests from localhost and configurable production domains.
- **API Base URL:** The frontend uses Vite's proxy for local development and NGINX reverse-proxying (`/api/`) for production Docker deployments.

---

## 14. Verification & Validation Summary

| Requirement | Implementation Status | Verification Method |
| :--- | :--- | :--- |
| **Official Elexon API** | Verified live & integrated | Live API probe retrieved 240 FUELHH & 4,672 WINDFOR records |
| **7-Day Query Limit** | Implemented with 6-day chunker | Tested against Elexon 400 error limit and chunked cleanly |
| **Decision Cutoff Logic** | Implemented & tested | Unit tests pass; evaluated live data at 2025-12-31 12:00 UTC |
| **Look-Ahead Prevention** | Implemented & verified | Post-cutoff records strictly excluded; no silent fallbacks |
| **DST Transitions** | Implemented (46/48/50 SPs) | Python `zoneinfo` verified for Spring/Autumn 2026 transitions |
| **Accuracy Calculations**| MAE, RMSE, Bias, WAPE, Coverage | Hand-verified mathematical tests in `test_metrics.py` |
| **4 Screens (A, B, C, D)**| Completed with Antigravity UI | Overview, Accuracy, Vintages History, Data Status |
| **CSV Export** | Implemented & tested | GET `/api/v1/export` exports exact matching format |
| **Automated Tests** | 22 Backend + 7 Frontend tests | `pytest` and `npm test` execute 100% green |
| **Docker Compose** | Production Dockerfiles authored | Docker compose with healthchecks & persistent volume |

---

## 15. AI Tool & Skill Disclosure

- **Design Guidance:** The interface architecture, color palette, glassmorphism surfaces, and typography were designed following the instructions of the `antigravity-design-expert` skill.
- **Assisting Coding Agent:** Developed using the Antigravity advanced agentic coding environment with Python 3.13, Node 26, Vite, and FastAPI.
- **Live Verification Note:** Real live data from the official Elexon BMRS API was successfully retrieved and validated during development. Docker execution was not tested directly inside the container because the local development host did not have the Docker daemon installed in PATH.
