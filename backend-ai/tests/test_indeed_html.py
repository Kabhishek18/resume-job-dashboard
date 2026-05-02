from unittest.mock import MagicMock

import httpx
import pytest
import respx

from app.core.config import settings
from app.services.jobs.collectors.indeed_html import collect_indeed_html
from app.services.jobs.collectors.jobspy_collector import _skip_redundant_indeed_html_note
from app.services.jobs.collectors.types import normalize_portal_id


def test_normalize_portal_bd_jobs_alias():
    assert normalize_portal_id("bd_jobs") == "bdjobs"
    assert normalize_portal_id("google") == "google"


@respx.mock
def test_collect_indeed_html_parses_job_card(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "jobspy_country_indeed", "india")
    monkeypatch.setattr(settings, "indeed_html_fallback_enabled", True)
    monkeypatch.setattr(settings, "indeed_html_max_listings", 18)

    html = (
        '<html><body><!-- ' + "x" * 250 + ' --><div class="job_seen_beacon">'
        '<a class="jcs-JobTitle" href="/viewjob?jk=abc123">Engineer</a>'
        '<div class="job-snippet">Do things</div>'
        "</div></body></html>"
    )
    respx.get(url__regex=r"https://in\.indeed\.com/jobs\?.*").mock(
        return_value=httpx.Response(200, text=html, headers={"content-type": "text/html"})
    )

    rows, note = collect_indeed_html({"keywords": "python", "locations": "Mumbai"})
    assert note is None
    assert len(rows) == 1
    assert rows[0].title == "Engineer"
    assert rows[0].portal == "indeed"
    assert "abc123" in rows[0].apply_url or "viewjob" in rows[0].apply_url


def test_collect_indeed_html_disabled_returns_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "indeed_html_fallback_enabled", False)
    rows, note = collect_indeed_html({"keywords": "x", "locations": "y"})
    assert rows == []
    assert note is None


def test_skip_redundant_indeed_html_note_when_jobspy_already_403():
    assert _skip_redundant_indeed_html_note(
        "Job search failed: indeed: bad response with status code: 403",
        "Indeed HTML: HTTPStatusError",
        False,
    )
    assert not _skip_redundant_indeed_html_note(
        "Job search failed: zip_recruiter: 403",
        "Indeed HTML: HTTPStatusError",
        False,
    )
    assert not _skip_redundant_indeed_html_note(
        "Job search failed: indeed: 403",
        "Indeed HTML: HTTPStatusError",
        True,
    )
    assert not _skip_redundant_indeed_html_note(
        "Job search failed: indeed: bad response with status code: 403",
        "Indeed HTML: no listings parsed (markup or block)",
        False,
    )


def test_collect_indeed_html_passes_jobspy_proxy_to_httpx(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "jobspy_country_indeed", "india")
    monkeypatch.setattr(settings, "indeed_html_fallback_enabled", True)
    monkeypatch.setattr(settings, "indeed_html_max_listings", 18)
    monkeypatch.setattr(settings, "jobspy_proxy", "http://127.0.0.1:9999")

    html = (
        '<html><body><!-- ' + "x" * 250 + ' --><div class="job_seen_beacon">'
        '<a class="jcs-JobTitle" href="/viewjob?jk=pxy99">Proxy job</a>'
        '<div class="job-snippet">Snippet</div>'
        "</div></body></html>"
    )

    mock_client_class = MagicMock()
    mock_inst = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    mock_inst.get.return_value = mock_resp
    mock_client_class.return_value.__enter__.return_value = mock_inst
    mock_client_class.return_value.__exit__.return_value = False

    monkeypatch.setattr("app.services.jobs.collectors.indeed_html.httpx.Client", mock_client_class)

    rows, note = collect_indeed_html({"keywords": "python", "locations": "Mumbai"})
    assert note is None
    assert len(rows) == 1
    assert mock_client_class.call_count >= 1
    assert mock_client_class.call_args.kwargs.get("proxy") == "http://127.0.0.1:9999"
