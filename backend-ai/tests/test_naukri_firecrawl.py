"""Tests for Firecrawl client and Naukri HTML collector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.core.config import settings
from app.services.jobs.collectors.jobspy_collector import collect_jobspy
from app.services.jobs.collectors.naukri_html import (
    collect_naukri_html,
    parse_naukri_serp_html,
    stable_key_from_url,
    _split_title_company,
)
from app.services.jobs.collectors.types import CollectedRow
from app.services.jobs.firecrawl_client import firecrawl_configured, scrape_url_to_markdown


def test_split_title_company():
    assert _split_title_company("Senior Dev at Acme Corp") == ("Senior Dev", "Acme Corp")
    assert _split_title_company("Backend | Contoso") == ("Backend", "Contoso")
    tit, comp = _split_title_company("Plain title only")
    assert tit == "Plain title only" and comp == ""


def test_parse_naukri_serp_html_data_company():
    html = """
    <div data-company="Gamma Labs">
      <a href="https://www.naukri.com/job-listings/sde-kolkata-123">Software Engineer</a>
    </div>
    """
    rows = parse_naukri_serp_html(html, max_listings=10)
    assert len(rows) == 1
    assert rows[0].title == "Software Engineer"
    assert rows[0].company == "Gamma Labs"
    assert "naukri.com" in rows[0].url


def test_parse_naukri_serp_html_comp_name_class():
    html = """
    <div class="cust-job-tuple">
      <a href="/job-listings/foo-bar-9990123">Product Manager</a>
      <span class="comp-name">Delta Tech</span>
    </div>
    """
    rows = parse_naukri_serp_html(html, max_listings=10)
    assert len(rows) == 1
    assert rows[0].title == "Product Manager"
    assert rows[0].company == "Delta Tech"


def test_stable_key_from_url():
    assert "naukri.com" in stable_key_from_url("https://www.naukri.com/job-listings/foo-123")


@patch("app.services.jobs.firecrawl_client.settings")
def test_firecrawl_configured(mock_settings):
    mock_settings.firecrawl_enabled = True
    mock_settings.firecrawl_api_key = "k"
    assert firecrawl_configured() is True

    mock_settings.firecrawl_api_key = "  "
    assert firecrawl_configured() is False

    mock_settings.firecrawl_api_key = "k"
    mock_settings.firecrawl_enabled = False
    assert firecrawl_configured() is False


@patch("app.services.jobs.firecrawl_client.httpx.Client")
def test_scrape_url_to_markdown_success(mock_client_cls, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "firecrawl_api_key", "fc-test-key", raising=False)
    monkeypatch.setattr(settings, "firecrawl_api_url", "https://api.firecrawl.dev", raising=False)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "success": True,
        "data": {"markdown": "# Hi\n\n[job](https://www.naukri.com/job-listings/x)", "metadata": {"title": "T"}},
    }
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    title, md = scrape_url_to_markdown("https://example.com")
    assert title == "T"
    assert "naukri.com" in md


@patch("app.services.jobs.firecrawl_client.httpx.Client")
def test_scrape_url_to_markdown_success_false(mock_client_cls, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "firecrawl_api_key", "fc-key", raising=False)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": False, "error": "rate limited"}
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    with pytest.raises(ValueError, match="rate"):
        scrape_url_to_markdown("https://example.com")


@patch("app.services.jobs.collectors.naukri_html._search_naukri_async")
def test_collect_naukri_html_maps_to_collected_rows(mock_search, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "naukri_html_enabled", True, raising=False)

    from app.services.jobs.collectors.naukri_html import _NaukriListing

    async def _fake(_p):
        return [
            _NaukriListing(
                title="Engineer",
                url="https://www.naukri.com/job-listings/abc-123",
                description="x",
                company="Acme",
            ),
        ]

    mock_search.side_effect = _fake

    rows, note = collect_naukri_html({"keywords": "python", "locations": "Pune"})
    assert len(rows) == 1
    assert rows[0].portal == "naukri"
    assert rows[0].title == "Engineer"
    assert rows[0].company == "Acme"
    assert "naukri.com" in rows[0].apply_url


@patch("app.services.jobs.collectors.jobspy_collector.collect_naukri_html")
@patch("app.services.jobs.collectors.jobspy_collector._scrape_jobs")
def test_collect_jobspy_merges_naukri_with_linkedin(mock_scrape, mock_naukri):
    mock_scrape.return_value = pd.DataFrame(
        [{"site": "linkedin", "title": "L", "company": "C", "location": "", "job_url": "https://li/j"}]
    )
    mock_naukri.return_value = (
        [
            CollectedRow(
                title="Naukri job",
                company="NaukriCo",
                location="India",
                portal="naukri",
                apply_url="https://www.naukri.com/job-listings/z-1",
                source_url="https://www.naukri.com/job-listings/z-1",
            )
        ],
        None,
    )

    rows, outcomes, _note = collect_jobspy(
        {"selected_portals": ["linkedin", "naukri"], "keywords": "dev", "locations": "", "remote_only": False}
    )

    assert len(rows) == 2
    assert outcomes["linkedin"].state == "ok"
    assert outcomes["naukri"].state == "ok"
    assert {r.portal for r in rows} == {"linkedin", "naukri"}
