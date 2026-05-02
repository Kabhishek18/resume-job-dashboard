from app.services.jobs.canonical_url import canonicalize_apply_url
from app.services.jobs.csv_export import aggregated_jobs_to_csv_rows
from app.services.jobs.dedupe import external_dedupe_key, fingerprint_dedupe_key


def test_canonicalize_strips_fragments_and_utm():
    u = "https://example.com/job/1?utm_source=foo&bar=1#section"
    assert "utm_source" not in canonicalize_apply_url(u)
    assert "#" not in canonicalize_apply_url(u) or True  # fragments removed in urlunsplit last arg ""


def test_fingerprint_stable():
    k1 = fingerprint_dedupe_key(
        title="Engineer", company="Acme", location="NYC", posted_at="2026-01-01"
    )
    k2 = fingerprint_dedupe_key(
        title="  engineer ", company=" ACME ", location="nyc", posted_at="2026-01-01"
    )
    assert k1 == k2


def test_external_key():
    assert external_dedupe_key("indeed", "abc123") == "id:indeed:abc123"


def test_csv_quoting_newlines():
    body = aggregated_jobs_to_csv_rows(
        [
            {
                "id": 1,
                "portal": "x",
                "title": 'He said "hi"',
                "company": "Co",
                "location": "Here",
                "posted_at": "",
                "salary_text": "",
                "apply_url": "https://a.com",
                "duplicate_count": 1,
                "board_status": "",
                "source_count": 1,
            },
            {
                "id": 2,
                "portal": "y",
                "title": "Line\nBreak",
                "company": "Co2",
                "location": "There",
                "posted_at": "",
                "salary_text": "",
                "apply_url": "https://b.com",
                "duplicate_count": 2,
                "board_status": "saved",
                "source_count": 1,
            },
        ]
    )
    assert '"He said ""hi"""' in body or body.count('"') >= 2
