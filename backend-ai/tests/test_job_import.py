import httpx
import respx
from fastapi.testclient import TestClient

from app.main import app


def test_import_preview_localhost_blocked():
    c = TestClient(app)
    r = c.post("/api/jobs/import-preview", json={"url": "http://127.0.0.1:8080/job"})
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "fallback_required"
    assert data["warnings"]


@respx.mock
def test_import_preview_html_extracted():
    html_url = "https://example.com/postings/stub-role"
    respx.get(html_url).mock(
        return_value=httpx.Response(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"""<!DOCTYPE html><html><head><title>Senior Dev | Globex Corp</title></head>
<body><main><article><p>""" + (b"Lorem ipsum engineer role responsibilities. " * 10)
            + b"""</p><p>Duties Python FastAPI Postgres.</p></article></main></body></html>""",
        )
    )
    c = TestClient(app)
    r = c.post("/api/jobs/import-preview", json={"url": html_url})
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "v1"
    assert body["mode"] == "imported_full"
    assert body["raw_text"]
    assert "Python" in body["raw_text"]
    assert body.get("title") is not None
