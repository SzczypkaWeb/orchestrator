from fastapi.testclient import TestClient

import control_server


def test_list_run_history_returns_events(monkeypatch):
    async def fake_fetch_run_events():
        return [
            {
                "run_id": "abc123",
                "repo": "backend",
                "node": "writer",
                "provider": "claude",
                "status": "success",
                "detail": None,
                "pr_url": "https://github.com/x/pull/1",
            }
        ]

    monkeypatch.setattr(control_server, "fetch_run_events", fake_fetch_run_events)

    client = TestClient(control_server.app)
    response = client.get("/runs")

    assert response.status_code == 200
    assert response.json() == {
        "events": [
            {
                "run_id": "abc123",
                "repo": "backend",
                "node": "writer",
                "provider": "claude",
                "status": "success",
                "detail": None,
                "pr_url": "https://github.com/x/pull/1",
            }
        ]
    }


def test_get_pr_status_returns_merged(monkeypatch):
    async def fake_fetch_pr_status(pr_url: str) -> str:
        assert pr_url == "https://github.com/x/y/pull/1"
        return "merged"

    monkeypatch.setattr(control_server, "fetch_pr_status", fake_fetch_pr_status)

    client = TestClient(control_server.app)
    response = client.get("/pr-status", params={"url": "https://github.com/x/y/pull/1"})

    assert response.status_code == 200
    assert response.json() == {"status": "merged"}


def test_get_run_metrics_returns_metrics_for_run(monkeypatch):
    async def fake_fetch_run_metrics(run_id: str):
        assert run_id == "abc123"
        return [
            {
                "node": "writer",
                "provider": "claude",
                "model": "claude-sonnet-5",
                "input_tokens": 1200,
                "output_tokens": 340,
                "total_cost_usd": 0.0456,
                "duration_ms": 8123,
                "success": True,
                "error_message": None,
                "created_at": "2026-09-16T12:00:00+00:00",
            }
        ]

    monkeypatch.setattr(control_server, "fetch_run_metrics", fake_fetch_run_metrics)

    client = TestClient(control_server.app)
    response = client.get("/runs/abc123/metrics")

    assert response.status_code == 200
    assert response.json()["metrics"][0]["node"] == "writer"
    assert response.json()["metrics"][0]["total_cost_usd"] == 0.0456


def test_complete_run_broadcasts_manually_completed_event(monkeypatch):
    captured = {}

    async def fake_broadcast(event):
        captured.update(event)

    monkeypatch.setattr(control_server, "broadcast", fake_broadcast)

    client = TestClient(control_server.app)
    response = client.post("/runs/complete", json={"run_id": "abc123", "repo": "backend"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert captured["run_id"] == "abc123"
    assert captured["repo"] == "backend"
    assert captured["node"] == "manually_completed"
    assert captured["status"] == "success"


def test_record_pr_merged_broadcasts_pr_merged_event(monkeypatch):
    captured = {}

    async def fake_broadcast(event):
        captured.update(event)

    monkeypatch.setattr(control_server, "broadcast", fake_broadcast)

    client = TestClient(control_server.app)
    response = client.post(
        "/runs/pr-merged",
        json={"run_id": "abc123", "repo": "backend", "pr_url": "https://github.com/x/y/pull/1"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert captured["run_id"] == "abc123"
    assert captured["repo"] == "backend"
    assert captured["node"] == "pr_merged"
    assert captured["status"] == "success"
    assert captured["pr_url"] == "https://github.com/x/y/pull/1"