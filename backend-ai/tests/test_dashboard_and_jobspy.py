import uuid
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.jobs.collectors.types import CollectedRow, PortalRunOutcome

client = TestClient(app)


def test_normalize_portal_id_zip_recruiter_and_aliases():
    from app.services.jobs.collectors.types import normalize_portal_id

    assert normalize_portal_id("zip_recruiter") == "zip_recruiter"
    assert normalize_portal_id("ZIP_RECRUITER") == "zip_recruiter"
    assert normalize_portal_id("ziprecruiter") == "zip_recruiter"
    assert normalize_portal_id("zip recruiter") == "zip_recruiter"
    assert normalize_portal_id("linkedin") == "linkedin"


@pytest.fixture
def enable_jobspy_indeed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that expect Indeed to be scraped must opt in (defaults to off)."""
    monkeypatch.setattr(settings, "jobspy_run_indeed", True)


def _register_tok() -> str:
    email = f"ds-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "x",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert r.status_code == 200
    return str(r.json()["access_token"])


def test_dashboard_summary_requires_auth():
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 401


@patch("app.services.jobs.run_service.run_collectors_for_profile")
def test_dashboard_summary_counts_and_recent(mock_collect):
    mock_collect.return_value = (
        [
            CollectedRow(
                title="T1",
                company="Co",
                location="L",
                portal="linkedin",
                apply_url="https://example.invalid/j/1",
                source_url="https://li",
            )
        ],
        {"linkedin": PortalRunOutcome(row_count=1, state="ok")},
        None,
    )

    t = _register_tok()
    h = {"Authorization": f"Bearer {t}"}

    pr = client.post(
        "/api/jobs/searches",
        json={"name": "S1", "keywords": "python", "locations": "Berlin", "selected_portals": ["linkedin"]},
        headers=h,
    )
    assert pr.status_code == 200
    pid = pr.json()["id"]
    rr = client.post(f"/api/jobs/searches/{pid}/run", headers=h)
    assert rr.status_code == 200
    run_id = rr.json()["id"]

    res = client.get(f"/api/jobs/runs/{run_id}/results", headers=h)
    jid = res.json()[0]["id"]
    client.post("/api/jobs/board", json={"job_id": jid}, headers=h)

    dash = client.get("/api/dashboard/summary", headers=h)
    assert dash.status_code == 200
    body = dash.json()
    assert body["total_tracked_jobs"] == 1
    assert body["board_counts_by_status"]["saved"] == 1
    assert len(body["recent_board_entries"]) == 1
    assert body["most_recent_run"]["id"] == run_id


@pytest.fixture
def enable_jobspy_zip_recruiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that expect ZipRecruiter to be scraped must opt in (defaults to off)."""
    monkeypatch.setattr(settings, "jobspy_run_zip_recruiter", True)


@patch("app.services.jobs.collectors.jobspy_collector._jobspy_supported_site_values", return_value=frozenset({"linkedin", "indeed", "zip_recruiter", "glassdoor"}))
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_zip_recruiter_passed_to_scrape(mock_scrape, _supported, enable_jobspy_zip_recruiter):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    mock_scrape.return_value = pd.DataFrame(
        [{"site": "zip_recruiter", "title": "Z", "company": "Y", "location": "", "job_url": "https://zr.example/j1"}]
    )
    rows, outcomes, note = collect_jobspy(
        {"selected_portals": ["zip_recruiter"], "keywords": "k", "remote_only": False}
    )
    mock_scrape.assert_called_once()
    assert mock_scrape.call_args.kwargs["site_name"] == ["zip_recruiter"]
    assert len(rows) == 1
    assert rows[0].portal == "zip_recruiter"
    assert outcomes["zip_recruiter"].state == "ok"
    assert outcomes["zip_recruiter"].row_count == 1
    assert note is None


@patch("app.services.jobs.collectors.jobspy_collector._jobspy_supported_site_values", return_value=frozenset({"linkedin", "indeed", "zip_recruiter", "glassdoor"}))
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_zip_recruiter_not_scraped_by_default(mock_scrape, _supported, monkeypatch: pytest.MonkeyPatch):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    monkeypatch.setattr(settings, "jobspy_run_indeed", True)
    monkeypatch.setattr(settings, "jobspy_run_zip_recruiter", False)
    mock_scrape.return_value = pd.DataFrame(
        [{"site": "linkedin", "title": "T", "company": "C", "location": "", "job_url": "https://u"}]
    )
    rows, outcomes, note = collect_jobspy(
        {"selected_portals": ["zip_recruiter", "linkedin"], "keywords": "python", "remote_only": False}
    )
    mock_scrape.assert_called_once()
    assert mock_scrape.call_args.kwargs["site_name"] == ["linkedin"]
    assert len(rows) == 1
    assert outcomes["zip_recruiter"].state == "no_results"
    assert note is not None
    assert "JOBSPY_RUN_ZIP_RECRUITER" in (note or "")


@patch("app.services.jobs.collectors.jobspy_collector.collect_naukri_html", return_value=([], None))
@patch("app.services.jobs.collectors.jobspy_collector.collect_indeed_html")
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_indeed_html_merges_after_jobspy_indeed_fails(mock_scrape, mock_indeed_html, _mock_naukri, enable_jobspy_indeed, monkeypatch: pytest.MonkeyPatch):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    monkeypatch.setattr(settings, "indeed_html_fallback_enabled", True)
    mock_scrape.side_effect = RuntimeError("bad response with status code: 403")
    mock_indeed_html.return_value = (
        [
            CollectedRow(
                title="HTML Job",
                company="",
                location="",
                portal="indeed",
                apply_url="https://in.indeed.com/viewjob?jk=xyz",
                source_url="https://in.indeed.com/viewjob?jk=xyz",
            )
        ],
        None,
    )
    rows, outcomes, note = collect_jobspy({"selected_portals": ["indeed"], "keywords": "k", "remote_only": False})

    assert len(rows) == 1
    assert rows[0].title == "HTML Job"
    assert outcomes["indeed"].state == "ok"
    assert outcomes["indeed"].row_count == 1
    mock_indeed_html.assert_called_once()


@patch("app.services.jobs.collectors.jobspy_collector._jobspy_supported_site_values", return_value=frozenset({"linkedin", "indeed", "google"}))
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_google_passed_to_scrape(mock_scrape, _supported):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    mock_scrape.return_value = pd.DataFrame(
        [{"site": "google", "title": "G", "company": "Co", "location": "", "job_url": "https://example.invalid/g1"}]
    )
    rows, outcomes, note = collect_jobspy({"selected_portals": ["google"], "keywords": "k", "remote_only": False})
    mock_scrape.assert_called_once()
    assert mock_scrape.call_args.kwargs["site_name"] == ["google"]
    assert len(rows) == 1
    assert rows[0].portal == "google"
    assert outcomes["google"].state == "ok"
    assert note is None


@patch("app.services.jobs.collectors.jobspy_collector.collect_indeed_html", return_value=([], None))
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_maps_dataframe(mock_scrape, _mock_indeed_html, enable_jobspy_indeed):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    mock_scrape.side_effect = [
        pd.DataFrame(
            [
                {
                    "site": "linkedin",
                    "title": "Engineer",
                    "company": "Acme",
                    "location": "NYC",
                    "job_url": "https://example.com/j1",
                    "job_url_direct": "https://example.com/j1-direct",
                    "date_posted": None,
                    "description": "Hello\tworld",
                    "id": "abc-123",
                    "interval": None,
                    "min_amount": None,
                    "max_amount": None,
                    "currency": None,
                }
            ]
        ),
        pd.DataFrame(),
    ]

    rows, outcomes, note = collect_jobspy(
        {"selected_portals": ["linkedin", "indeed"], "keywords": "dev", "locations": "NY", "remote_only": False}
    )

    assert mock_scrape.call_count == 2

    assert len(rows) == 1
    assert note is None
    assert rows[0].title == "Engineer"
    assert rows[0].apply_url == "https://example.com/j1-direct"
    assert rows[0].external_job_id == "abc-123"
    assert outcomes["linkedin"].state == "ok"
    assert outcomes["linkedin"].row_count == 1
    assert outcomes["indeed"].state == "no_results"
    assert outcomes["indeed"].row_count == 0


@patch("app.services.jobs.collectors.jobspy_collector.collect_naukri_html")
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_no_scrape_when_only_unsupported_portals(mock_scrape, mock_naukri):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    mock_naukri.return_value = ([], None)

    rows, outcomes, note = collect_jobspy(
        {"selected_portals": ["glassdoor", "naukri"], "keywords": "dev", "remote_only": False}
    )

    assert rows == []
    mock_scrape.assert_not_called()
    mock_naukri.assert_called_once()
    assert outcomes["glassdoor"].state == "unavailable"
    assert outcomes["naukri"].state == "no_results"


@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_passes_only_supported_sites_to_scrape(mock_scrape):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    mock_scrape.return_value = pd.DataFrame(
        [{"site": "linkedin", "title": "X", "company": "Y", "location": "", "job_url": "https://u"}]
    )
    collect_jobspy(
        {"selected_portals": ["linkedin", "glassdoor"], "keywords": "k", "locations": "Vancouver", "remote_only": True}
    )
    mock_scrape.assert_called_once()
    k = mock_scrape.call_args.kwargs
    assert k["site_name"] == ["linkedin"]
    assert k["location"] == "Vancouver"
    assert k["is_remote"] is True
    assert "verbose" not in k


@patch("app.services.jobs.collectors.jobspy_collector.collect_indeed_html", return_value=([], None))
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_indeed_403_linkedin_still_returns_rows(mock_scrape, _mock_indeed_html, enable_jobspy_indeed):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    li_df = pd.DataFrame(
        [{"site": "linkedin", "title": "T", "company": "C", "location": "", "job_url": "https://u", "job_url_direct": None}]
    )
    # sites_arg is sorted linkedin-first
    mock_scrape.side_effect = [li_df, Exception("bad response with status code: 403")]

    rows, outcomes, note = collect_jobspy(
        {"selected_portals": ["indeed", "linkedin"], "keywords": "python", "remote_only": False}
    )

    assert mock_scrape.call_count == 2
    assert len(rows) == 1
    assert outcomes["indeed"].state == "unavailable"
    assert outcomes["linkedin"].state == "ok"
    assert note is not None
    assert "403" in (note or "") or "Indeed" in (note or "")


@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_indeed_not_scraped_by_default(mock_scrape, monkeypatch: pytest.MonkeyPatch):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    monkeypatch.setattr(settings, "jobspy_run_indeed", False)
    mock_scrape.return_value = pd.DataFrame(
        [{"site": "linkedin", "title": "T", "company": "C", "location": "", "job_url": "https://u"}]
    )
    rows, outcomes, note = collect_jobspy(
        {"selected_portals": ["indeed", "linkedin"], "keywords": "python", "remote_only": False}
    )

    mock_scrape.assert_called_once()
    assert mock_scrape.call_args.kwargs["site_name"] == ["linkedin"]
    assert len(rows) == 1
    assert outcomes["linkedin"].state == "ok"
    assert outcomes["indeed"].state == "no_results"
    assert note is not None
    assert "JOBSPY_RUN_INDEED" in (note or "")


@patch("app.services.jobs.collectors.jobspy_collector.collect_linkedin_guest")
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_marks_unavailable_on_scrape_error(mock_scrape, mock_guest):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy
    from app.services.jobs.collectors.types import CollectorResult

    mock_scrape.side_effect = RuntimeError("blocked")
    mock_guest.return_value = CollectorResult(rows=[], warnings=["linkedin_empty"])

    rows, outcomes, note = collect_jobspy({"selected_portals": ["linkedin"], "keywords": "x", "remote_only": False})

    assert rows == []
    assert outcomes["linkedin"].state == "unavailable"
    assert note is not None
    assert "blocked" in (note or "")


@patch("app.services.jobs.collectors.jobspy_collector.collect_linkedin_guest")
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_linkedin_guest_fills_when_jobspy_fails(mock_scrape, mock_guest):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy
    from app.services.jobs.collectors.types import CollectorResult, CollectedRow

    mock_scrape.side_effect = RuntimeError("blocked")
    mock_guest.return_value = CollectorResult(
        rows=[
            CollectedRow(
                title="Engineer",
                company="Acme",
                location="Berlin",
                portal="linkedin",
                apply_url="https://www.linkedin.com/jobs/view/1",
                source_url="https://www.linkedin.com/jobs/view/1",
            )
        ],
        warnings=[],
    )

    rows, outcomes, note = collect_jobspy({"selected_portals": ["linkedin"], "keywords": "x", "remote_only": False})
    assert len(rows) == 1
    assert rows[0].title == "Engineer"
    assert outcomes["linkedin"].state == "ok"


@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_jobspy_collector_retries_without_proxy_on_proxy_failure(
    mock_scrape, monkeypatch: pytest.MonkeyPatch
):
    from app.services.jobs.collectors.jobspy_collector import collect_jobspy

    monkeypatch.setattr(settings, "jobspy_proxy", "http://127.0.0.1:8888")
    mock_scrape.side_effect = [
        RuntimeError("ProxyError: HTTPConnectionPool(host='127.0.0.1', port=8888): Max retries exceeded"),
        pd.DataFrame([{"site": "linkedin", "title": "Engineer", "company": "Acme", "location": "", "job_url": "https://u"}]),
    ]

    rows, outcomes, note = collect_jobspy({"selected_portals": ["linkedin"], "keywords": "x", "remote_only": False})

    assert len(rows) == 1
    assert outcomes["linkedin"].state == "ok"
    assert mock_scrape.call_count == 2
    first_call = mock_scrape.call_args_list[0].kwargs
    second_call = mock_scrape.call_args_list[1].kwargs
    assert first_call["proxy"] == "http://127.0.0.1:8888"
    assert "proxy" not in second_call
    assert note is not None
    assert "JOBSPY_PROXY" in note
