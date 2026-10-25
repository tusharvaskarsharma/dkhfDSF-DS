import pytest
import threading
import subprocess
import sys
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app, app
from app.data.database import init_db
from app.data.fixtures.fixture_loader import load_fixture_data_into_db
import app.data.repository as repo
import app.data.fixtures.fixture_loader as fixture_loader


# ============================================================================
# 1. Tests for .gitignore Configuration
# ============================================================================

def test_gitignore_tracks_backend_data_and_ignores_db_and_env():
    """Verify git check-ignore correctly allows backend/app/data and ignores runtime artifacts."""
    # Run git check-ignore on backend source files (must return exit code 1 = not ignored)
    tracked_candidates = [
        "backend/app/data/database.py",
        "backend/app/data/repository.py",
        "backend/app/data/fixtures/fixture_loader.py"
    ]
    res_tracked = subprocess.run(
        ["git", "check-ignore", "-v"] + tracked_candidates,
        capture_output=True,
        text=True
    )
    # When none of the files are ignored, git check-ignore exits with code 1
    assert res_tracked.returncode == 1, (
        f"Backend source files should NOT be ignored by git! Found:\n{res_tracked.stdout}"
    )

    # Run git check-ignore on files that MUST be ignored (must return exit code 0)
    ignored_candidates = [
        "data/wind_forecast.db",
        ".env"
    ]
    res_ignored = subprocess.run(
        ["git", "check-ignore", "-v"] + ignored_candidates,
        capture_output=True,
        text=True
    )
    assert res_ignored.returncode == 0, (
        f"Database and .env files MUST be ignored by git! stderr: {res_ignored.stderr}"
    )
    assert "data/wind_forecast.db" in res_ignored.stdout
    assert ".env" in res_ignored.stdout


# ============================================================================
# 2. Tests for CORS Security, Origins, Wildcards, and Credentials
# ============================================================================

def test_cors_valid_origins_receive_credentials():
    """Verify that permitted origins receive Access-Control-Allow-Origin and credentials header."""
    custom_settings = Settings(
        CORS_ORIGINS=["http://localhost:5173", "https://portal.winddesk.energy"],
        CORS_ALLOW_CREDENTIALS=True
    )
    test_app = create_app(custom_settings)
    client = TestClient(test_app)

    # Simple GET request with allowed origin
    resp = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Second allowed origin
    resp2 = client.get("/", headers={"Origin": "https://portal.winddesk.energy"})
    assert resp2.status_code == 200
    assert resp2.headers.get("access-control-allow-origin") == "https://portal.winddesk.energy"
    assert resp2.headers.get("access-control-allow-credentials") == "true"


def test_cors_untrusted_origin_rejected():
    """Verify that requests from unapproved origins do not receive allow-origin header."""
    custom_settings = Settings(
        CORS_ORIGINS=["http://localhost:5173"],
        CORS_ALLOW_CREDENTIALS=True
    )
    test_app = create_app(custom_settings)
    client = TestClient(test_app)

    resp = client.get("/", headers={"Origin": "https://malicious-site.com"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers


def test_cors_preflight_options_request():
    """Verify OPTIONS preflight request for allowed vs disallowed origins."""
    custom_settings = Settings(
        CORS_ORIGINS=["http://localhost:5173"],
        CORS_ALLOW_CREDENTIALS=True
    )
    test_app = create_app(custom_settings)
    client = TestClient(test_app)

    # Preflight for allowed origin
    resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Preflight for untrusted origin
    resp_untrusted = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://untrusted.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert "access-control-allow-origin" not in resp_untrusted.headers


def test_cors_wildcard_rejected_when_credentials_enabled():
    """Verify that setting wildcard origin '*' fails validation when credentials are enabled."""
    # List containing wildcard
    with pytest.raises((ValidationError, ValueError)) as excinfo:
        Settings(CORS_ORIGINS=["*"], CORS_ALLOW_CREDENTIALS=True)
    assert "Wildcard '*' origin is prohibited" in str(excinfo.value)

    # String containing wildcard
    with pytest.raises((ValidationError, ValueError)) as excinfo:
        Settings(CORS_ORIGINS="*", CORS_ALLOW_CREDENTIALS=True)
    assert "Wildcard '*' origin is prohibited" in str(excinfo.value)

    # Mixed origins containing wildcard
    with pytest.raises((ValidationError, ValueError)) as excinfo:
        Settings(CORS_ORIGINS=["http://localhost:5173", "*"], CORS_ALLOW_CREDENTIALS=True)
    assert "Wildcard '*' origin is prohibited" in str(excinfo.value)

    # App factory validation
    class FakeSettings:
        PROJECT_NAME = "Test"
        API_V1_STR = "/api/v1"
        CORS_ORIGINS = ["*"]
        CORS_ALLOW_CREDENTIALS = True

    with pytest.raises(ValueError) as excinfo:
        create_app(FakeSettings())
    assert "Wildcard '*' origin is prohibited" in str(excinfo.value)


def test_cors_env_variable_parsing():
    """Verify parsing comma-separated string or JSON array from environment variables."""
    # Comma-separated string with whitespace
    s_csv = Settings(CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:5173, https://app.energy ")
    assert s_csv.CORS_ORIGINS == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://app.energy"
    ]

    # JSON array string
    s_json = Settings(CORS_ORIGINS='["http://localhost:5173", "https://app.energy"]')
    assert s_json.CORS_ORIGINS == [
        "http://localhost:5173",
        "https://app.energy"
    ]


def test_cors_default_configuration_safe():
    """Verify default settings do not include wildcard and contain local development ports."""
    default_settings = Settings()
    assert "*" not in default_settings.CORS_ORIGINS
    assert "http://localhost:5173" in default_settings.CORS_ORIGINS
    assert "http://127.0.0.1:5173" in default_settings.CORS_ORIGINS
    assert "http://localhost:3000" in default_settings.CORS_ORIGINS
    assert "http://localhost:8000" in default_settings.CORS_ORIGINS
    assert default_settings.CORS_ALLOW_CREDENTIALS is True


# ============================================================================
# 3. Tests for SQLite Event-Loop Blocking Prevention (Threadpool Offloading)
# ============================================================================

@pytest.fixture
def test_db_setup(tmp_path, monkeypatch):
    """Set up temporary SQLite database with fixtures loaded."""
    from app.core.config import settings
    test_db = str(tmp_path / "test_hotfixes_wind.db")
    monkeypatch.setattr(settings, "DATABASE_PATH", test_db)
    init_db()
    load_fixture_data_into_db()
    return test_db


def test_evaluate_forecasts_db_calls_run_in_worker_threads(test_db_setup, monkeypatch):
    """
    Verify that synchronous database calls in evaluate_forecasts are offloaded to
    worker threads (run_in_threadpool) and do NOT run on the main event loop thread.
    """
    import app.api.routes as routes_module

    main_thread_id = threading.main_thread().ident
    executed_threads = {}

    orig_get_actual = routes_module.get_actual_records
    orig_get_forecast = routes_module.get_forecast_records

    def spy_get_actual_records(*args, **kwargs):
        curr_thread = threading.current_thread()
        executed_threads["get_actual_records"] = {
            "thread_ident": curr_thread.ident,
            "is_main_thread": (curr_thread.ident == main_thread_id),
            "thread_name": curr_thread.name
        }
        return orig_get_actual(*args, **kwargs)

    def spy_get_forecast_records(*args, **kwargs):
        curr_thread = threading.current_thread()
        executed_threads["get_forecast_records"] = {
            "thread_ident": curr_thread.ident,
            "is_main_thread": (curr_thread.ident == main_thread_id),
            "thread_name": curr_thread.name
        }
        return orig_get_forecast(*args, **kwargs)

    monkeypatch.setattr(routes_module, "get_actual_records", spy_get_actual_records)
    monkeypatch.setattr(routes_module, "get_forecast_records", spy_get_forecast_records)

    client = TestClient(app)
    resp = client.get(
        "/api/v1/evaluation",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-01-02",
            "decision_cutoff": "2025-12-31T12:00:00Z",
            "granularity": "hourly",
            "mode": "auto"
        }
    )

    assert resp.status_code == 200
    assert "get_actual_records" in executed_threads
    assert "get_forecast_records" in executed_threads

    # Verify both database operations ran outside the main thread
    assert executed_threads["get_actual_records"]["is_main_thread"] is False, (
        f"get_actual_records ran on main thread! {executed_threads['get_actual_records']}"
    )
    assert executed_threads["get_forecast_records"]["is_main_thread"] is False, (
        f"get_forecast_records ran on main thread! {executed_threads['get_forecast_records']}"
    )


def test_evaluate_forecasts_demo_mode_threadpool(test_db_setup, monkeypatch):
    """Verify demo fixture loading in evaluate_forecasts is also offloaded to worker thread."""
    import app.api.routes as routes_module

    main_thread_id = threading.main_thread().ident
    executed_threads = {}

    orig_load_fixtures = routes_module.load_fixture_data_into_db

    def spy_load_fixtures(*args, **kwargs):
        curr_thread = threading.current_thread()
        executed_threads["load_fixture_data_into_db"] = {
            "thread_ident": curr_thread.ident,
            "is_main_thread": (curr_thread.ident == main_thread_id)
        }
        return orig_load_fixtures(*args, **kwargs)

    monkeypatch.setattr(routes_module, "load_fixture_data_into_db", spy_load_fixtures)

    client = TestClient(app)
    resp = client.get(
        "/api/v1/evaluation",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-01-02",
            "decision_cutoff": "2025-12-31T12:00:00Z",
            "mode": "demo"
        }
    )

    assert resp.status_code == 200
    assert "load_fixture_data_into_db" in executed_threads
    assert executed_threads["load_fixture_data_into_db"]["is_main_thread"] is False


def test_health_cache_stats_threadpool(test_db_setup, monkeypatch):
    """Verify get_cache_stats in /health is offloaded to worker thread."""
    import app.api.routes as routes_module

    main_thread_id = threading.main_thread().ident
    executed_threads = {}

    orig_get_cache_stats = routes_module.get_cache_stats

    def spy_get_cache_stats(*args, **kwargs):
        curr_thread = threading.current_thread()
        executed_threads["get_cache_stats"] = {
            "thread_ident": curr_thread.ident,
            "is_main_thread": (curr_thread.ident == main_thread_id)
        }
        return orig_get_cache_stats(*args, **kwargs)

    monkeypatch.setattr(routes_module, "get_cache_stats", spy_get_cache_stats)

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "get_cache_stats" in executed_threads
    assert executed_threads["get_cache_stats"]["is_main_thread"] is False


def test_evaluate_forecasts_calculations_and_schema_preserved(test_db_setup):
    """Verify accuracy metrics, schema structure, and error values are preserved exactly."""
    client = TestClient(app)
    resp = client.get(
        "/api/v1/evaluation",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-01-02",
            "decision_cutoff": "2025-12-31T12:00:00Z",
            "granularity": "hourly",
            "mode": "auto"
        }
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["date_from"] == "2026-01-01"
    assert data["date_to"] == "2026-01-02"
    assert data["granularity"] == "hourly"
    assert data["alignment_method"] == "native_hourly"

    metrics = data["metrics"]
    assert metrics["valid_pairs_count"] == 48 # 2 days * 24 hours
    assert metrics["coverage_pct"] == 100.0
    assert isinstance(metrics["mae_mw"], float)
    assert isinstance(metrics["rmse_mw"], float)
    assert isinstance(metrics["bias_mw"], float)
    assert isinstance(metrics["wape_pct"], float)
    assert len(data["intervals"]) == 48
    assert len(data["daily_breakdown"]) == 2
