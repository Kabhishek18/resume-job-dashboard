import json

import httpx
import respx
from fastapi.testclient import TestClient

from app.main import app


@respx.mock
def test_import_json_ld_jobposting_description():
    long_desc = "We seek a backend engineer skilled in Python FastAPI Postgres. Responsibilities APIs. " * 3
    ld = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Backend Engineer",
        "description": long_desc,
        "hiringOrganization": {"@type": "Organization", "name": "AcmeCorp"},
    }
    script_body = json.dumps(ld)
    html_url = "https://example.com/jobs/schema-test"
    respx.get(html_url).mock(
        return_value=httpx.Response(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=(
                '<html><head><title>Waste</title></head><body>'
                f'<script type="application/ld+json">{script_body}</script>'
                '<p>x</p></body></html>'
            ).encode("utf-8"),
        ),
    )
    c = TestClient(app)
    r = c.post("/api/jobs/import-preview", json={"url": html_url})
    assert r.status_code == 200
    j = r.json()
    assert j["mode"] == "imported_full"
    assert "FastAPI" in (j["raw_text"] or "")


@respx.mock
def test_import_partial_title_only_short_dom():
    html_url = "https://example.com/jobs/no-body"
    respx.get(html_url).mock(
        return_value=httpx.Response(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html><head><title>Senior Dev | TinyCo</title></head><body><p>Hi</p></body></html>",
        ),
    )
    c = TestClient(app)
    r = c.post("/api/jobs/import-preview", json={"url": html_url})
    assert r.status_code == 200
    j = r.json()
    assert j["mode"] in ("imported_partial", "fallback_required")
