import httpx
import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import logging
from app.core.config import settings
from app.core.time_utils import format_utc_iso, parse_utc_iso
from app.data.repository import upsert_actuals, upsert_forecasts, log_sync

logger = logging.getLogger("elexon_client")

class ElexonClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details

class ElexonClient:
    def __init__(self):
        self.base_url = settings.ELEXON_BASE_URL
        self.timeout = settings.ELEXON_TIMEOUT_SECONDS
        self.max_retries = settings.ELEXON_MAX_RETRIES
        self.retry_backoff = settings.ELEXON_RETRY_BACKOFF
        self.user_agent = "UKWindForecastAccuracyDashboard/1.0 (EnergyTradingAnalytics)"

    async def _request_with_retry(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP GET with bounded retries and exponential backoff for 429/5xx."""
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        return response.json()
                    
                    if response.status_code == 429:
                        wait = self.retry_backoff * (2 ** (attempt - 1))
                        logger.warning(f"Rate limited (429) on {url}. Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                        
                    if 500 <= response.status_code < 600:
                        wait = self.retry_backoff * (2 ** (attempt - 1))
                        logger.warning(f"Server error ({response.status_code}) on {url}. Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue

                    # Client error (400, 404, etc.)
                    error_detail = response.text[:400]
                    raise ElexonClientError(
                        f"Elexon API returned HTTP {response.status_code}: {error_detail}",
                        status_code=response.status_code,
                        details=error_detail
                    )
                except httpx.RequestError as exc:
                    if attempt == self.max_retries:
                        raise ElexonClientError(f"HTTP request failed after {self.max_retries} attempts: {exc}")
                    await asyncio.sleep(self.retry_backoff * attempt)

        raise ElexonClientError(f"Failed to fetch from {url} after {self.max_retries} retries")

    async def fetch_fuelhh_actuals(self, date_from_str: str, date_to_str: str) -> List[Dict[str, Any]]:
        """
        Fetch actual wind generation from FUELHH dataset.
        Enforces Elexon's <= 7 day query limit by chunking into 6-day slices.
        """
        d_start = date.fromisoformat(date_from_str)
        d_end = date.fromisoformat(date_to_str)
        if d_end < d_start:
            raise ValueError("date_to must be >= date_from")

        all_records = []
        curr = d_start
        url = f"{self.base_url}/datasets/FUELHH"

        while curr <= d_end:
            chunk_end = min(curr + timedelta(days=5), d_end)
            params = {
                "settlementDateFrom": curr.isoformat(),
                "settlementDateTo": chunk_end.isoformat(),
                "fuelType": "WIND"
            }
            logger.info(f"Fetching FUELHH chunk {params['settlementDateFrom']} to {params['settlementDateTo']}")
            
            try:
                data = await self._request_with_retry(url, params)
                items = data.get("data", [])
                for it in items:
                    # Filter to WIND
                    if it.get("fuelType") == "WIND":
                        all_records.append({
                            "dataset": "FUELHH",
                            "settlement_date": it["settlementDate"],
                            "settlement_period": int(it["settlementPeriod"]),
                            "delivery_time": it["startTime"],
                            "fuel_type": "WIND",
                            "generation_mw": float(it["generation"]),
                            "publish_time": it.get("publishTime", ""),
                            "retrieval_time": format_utc_iso(datetime.now(timezone.utc))
                        })
                log_sync("FUELHH", f"{params['settlementDateFrom']}..{params['settlementDateTo']}", len(items), "SUCCESS")
            except Exception as e:
                log_sync("FUELHH", f"{params['settlementDateFrom']}..{params['settlementDateTo']}", 0, "FAILED", str(e))
                raise

            curr = chunk_end + timedelta(days=1)

        # Cache in SQLite
        upsert_actuals(all_records)
        return all_records

    async def fetch_windfor_forecasts(self, publish_from_iso: str, publish_to_iso: str) -> List[Dict[str, Any]]:
        """
        Fetch wind forecast publication vintages from WINDFOR dataset.
        Enforces Elexon's <= 7 day query limit on publishDateTime.
        """
        dt_start = parse_utc_iso(publish_from_iso)
        dt_end = parse_utc_iso(publish_to_iso)
        if dt_end < dt_start:
            raise ValueError("publish_to must be >= publish_from")

        all_records = []
        seen_keys = set()
        curr = dt_start
        url = f"{self.base_url}/datasets/WINDFOR"

        while curr <= dt_end:
            chunk_end = min(curr + timedelta(days=5), dt_end)
            params = {
                "publishDateTimeFrom": format_utc_iso(curr),
                "publishDateTimeTo": format_utc_iso(chunk_end)
            }
            logger.info(f"Fetching WINDFOR chunk {params['publishDateTimeFrom']} to {params['publishDateTimeTo']}")

            try:
                data = await self._request_with_retry(url, params)
                items = data.get("data", []) or []
                for it in items:
                    rec_key = (it["publishTime"], it["startTime"])
                    if rec_key in seen_keys:
                        continue
                    seen_keys.add(rec_key)
                    all_records.append({
                        "dataset": "WINDFOR",
                        "publish_time": it["publishTime"],
                        "delivery_time": it["startTime"],
                        "generation_mw": float(it["generation"]),
                        "retrieval_time": format_utc_iso(datetime.now(timezone.utc)),
                        "source_status": "OK"
                    })
                log_sync("WINDFOR", f"{params['publishDateTimeFrom']}..{params['publishDateTimeTo']}", len(items), "SUCCESS")
            except Exception as e:
                log_sync("WINDFOR", f"{params['publishDateTimeFrom']}..{params['publishDateTimeTo']}", 0, "FAILED", str(e))
                raise

            if chunk_end >= dt_end:
                break
            curr = chunk_end

        # Cache in SQLite
        upsert_forecasts(all_records)
        return all_records

    async def check_api_health(self) -> Tuple[bool, Optional[float], Optional[str]]:
        """Check Elexon API responsiveness and latency."""
        url = f"{self.base_url}/datasets/FUELHH"
        today = date.today()
        # Query 1 single settlement date to verify connectivity
        params = {
            "settlementDateFrom": (today - timedelta(days=2)).isoformat(),
            "settlementDateTo": (today - timedelta(days=2)).isoformat(),
            "fuelType": "WIND"
        }
        headers = {"User-Agent": self.user_agent}
        start_time = asyncio.get_event_loop().time()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                latency = round((asyncio.get_event_loop().time() - start_time) * 1000, 1)
                if resp.status_code == 200:
                    return True, latency, None
                return False, latency, f"HTTP {resp.status_code}: {resp.text[:150]}"
        except Exception as e:
            return False, None, str(e)

elexon_client = ElexonClient()
