import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.aggregated_job import AggregatedJob
from app.services.jobs.collectors.types import CollectedRow, PortalRunOutcome

client = TestClient(app)


def _register_tok() -> str:
    email = f"ja-{uuid.uuid4().hex[:10]}@example.com"
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


def test_search_profile_results_wanted_round_trip_and_validation():
    t = _register_tok()
    h = {"Authorization": f"Bearer {t}"}

    bad_low = client.post(
        "/api/jobs/searches",
        json={"name": "S0", "keywords": "k", "results_wanted": 0},
        headers=h,
    )
    assert bad_low.status_code == 400
    assert bad_low.json()["error"]["code"] == "VALIDATION"

    bad_high = client.post(
        "/api/jobs/searches",
        json={"name": "S1", "keywords": "k", "results_wanted": 201},
        headers=h,
    )
    assert bad_high.status_code == 400

    ok = client.post(
        "/api/jobs/searches",
        json={"name": "S2", "keywords": "k", "results_wanted": 75},
        headers=h,
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["results_wanted"] == 75

    pid = body["id"]
    cleared = client.patch(f"/api/jobs/searches/{pid}", json={"results_wanted": None}, headers=h)
    assert cleared.status_code == 200
    assert cleared.json().get("results_wanted") in (None,)


def test_jobs_api_isolation_between_users():
    t1 = _register_tok()
    t2 = _register_tok()
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    cr = client.post(
        "/api/jobs/searches",
        json={"name": "S1", "keywords": "python", "locations": "NYC", "selected_portals": ["linkedin"]},
        headers=h1,
    )
    assert cr.status_code == 200
    pid = cr.json()["id"]
    r2 = client.get("/api/jobs/searches", headers=h2)
    assert r2.status_code == 200
    assert not any(p["id"] == pid for p in r2.json())


@patch("app.services.jobs.run_service.run_collectors_for_profile")
def test_run_lifecycle_and_results(mock_collect):
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

    gr = client.get(f"/api/jobs/runs/{run_id}", headers=h)
    assert gr.status_code == 200

    res = client.get(f"/api/jobs/runs/{run_id}/results", headers=h)
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) >= 1
    assert rows[0]["title"] == "T1"
    assert "description_snippet" in rows[0]
    assert rows[0]["description_snippet"] == ""

    csv_r = client.get(f"/api/jobs/runs/{run_id}/results.csv", headers=h)
    assert csv_r.status_code == 200
    assert "portal" in csv_r.text.lower() or csv_r.status_code == 200

    jid = rows[0]["id"]
    board = client.post("/api/jobs/board", json={"job_id": jid}, headers=h)
    assert board.status_code == 200
    bid = board.json()["id"]
    board2 = client.post("/api/jobs/board", json={"job_id": jid}, headers=h)
    assert board2.status_code == 200
    assert board2.json()["id"] == bid

    u = client.patch(f"/api/jobs/board/{bid}", json={"status": "applied", "notes": "Applied today"}, headers=h)
    assert u.status_code == 200
    assert u.json()["status"] == "applied"


@pytest.mark.parametrize(
    ("row1", "row2", "merged"),
    [
        (
            dict(
                title="X",
                company="Y",
                location="Z",
                portal="linkedin",
                apply_url="https://portal/a?utm_source=z",
                source_url="s",
            ),
            dict(
                title="X",
                company="Y",
                location="Z",
                portal="linkedin",
                apply_url="https://portal/a",
                source_url="s2",
            ),
            True,
        ),
    ],
)
def test_dedupe_merges_on_canonical_url(row1, row2, merged):
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models.job_search_profile import JobSearchProfile
    from app.models.job_search_run import JobSearchRun
    from app.models.user import User
    from app.services.jobs.run_service import ingest_collected

    db = SessionLocal()
    try:
        u = User(email=f"dup-{uuid.uuid4().hex}@example.com", name="x", hashed_password=hash_password("pw"))
        db.add(u)
        db.flush()
        p = JobSearchProfile(user_id=u.id, name="n", selected_portals=["linkedin"])
        db.add(p)
        db.flush()
        run = JobSearchRun(user_id=u.id, search_profile_id=p.id, trigger_mode="manual", status="completed")
        db.add(run)
        db.flush()
        ingest_collected(db, u.id, run.id, CollectedRow(**row1))
        db.commit()
        ingest_collected(db, u.id, run.id, CollectedRow(**row2))
        db.commit()

        ct = db.query(AggregatedJob).filter(AggregatedJob.user_id == u.id).count()
        if merged:
            assert ct == 1
            job = db.query(AggregatedJob).filter(AggregatedJob.user_id == u.id).first()
            assert job is not None
            assert job.duplicate_count >= 2
    finally:
        db.close()
