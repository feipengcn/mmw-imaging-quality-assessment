from pathlib import Path
import runpy
import sys
import io

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import manual_rating_auth
from app.manual_rating_auth import hash_password
from app.manual_rating_repository import ManualRatingRepository


class StubImageRepository:
    def __init__(self, records):
        self._records = list(records)

    def list_records(self):
        return list(self._records)

    def delete_image(self, image_id):
        for index, record in enumerate(self._records):
            if record["id"] == image_id:
                del self._records[index]
                return
        raise KeyError(image_id)

    def reset(self):
        self._records = []


def _make_client(repo: ManualRatingRepository, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "manual_rating_repository", repo)
    main.app.state.manual_rating_repository = repo
    return TestClient(main.app)


def build_manual_rating_context(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    admin = repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )
    reviewer = repo.create_user(
        username="reviewer",
        display_name="Reviewer",
        password_hash=hash_password("secret123"),
        role="reviewer",
    )
    monkeypatch.setattr(main, "repository", StubImageRepository([
        {"id": "img-1", "filename": "a.png", "experiment_group": "g1", "batch": "b1"},
        {"id": "img-2", "filename": "b.png", "experiment_group": "g1", "batch": "b1"},
    ]))
    client = _make_client(repo, monkeypatch)
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    dataset = client.post(
        "/api/manual/datasets",
        json={
            "name": "Dataset A",
            "image_ids": ["img-1", "img-2"],
            "experiment_group": "g1",
            "batch": "b1",
        },
    ).json()["dataset"]
    task = client.post(
        "/api/manual/tasks",
        json={
            "dataset_id": dataset["id"],
            "name": "Task A",
            "description": "",
            "reviewer_ids": [reviewer["id"]],
        },
    ).json()["task"]
    client.post("/api/auth/logout")
    return {
        "repo": repo,
        "client": client,
        "admin": admin,
        "reviewer": reviewer,
        "dataset_id": dataset["id"],
        "task_id": task["id"],
    }


def test_auth_login_sets_session_and_me_returns_user(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )
    repo.create_user(
        username="inactive",
        display_name="Inactive",
        password_hash=hash_password("secret123"),
        role="reviewer",
        active=False,
    )
    repo.create_user(
        username="broken-hash",
        display_name="Broken Hash",
        password_hash="zz:not-hex",
        role="reviewer",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    me = client.get("/api/auth/me")
    inactive_login = client.post("/api/auth/login", json={"username": "inactive", "password": "secret123"})
    broken_hash_login = client.post("/api/auth/login", json={"username": "broken-hash", "password": "secret123"})

    assert login.status_code == 200
    assert "set-cookie" in login.headers
    assert "session=" in login.headers["set-cookie"]
    assert "HttpOnly" in login.headers["set-cookie"]
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "admin"
    assert inactive_login.status_code == 401
    assert inactive_login.json()["detail"] == "invalid credentials"
    assert broken_hash_login.status_code == 401
    assert broken_hash_login.json()["detail"] == "invalid credentials"


def test_auth_logout_clears_session_cookie(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    logout = client.post("/api/auth/logout")
    me = client.get("/api/auth/me")

    assert login.status_code == 200
    assert logout.status_code == 200
    assert "set-cookie" in logout.headers
    assert "session=null" in logout.headers["set-cookie"]
    assert "Max-Age=0" in logout.headers["set-cookie"]
    assert "HttpOnly" in logout.headers["set-cookie"]
    assert me.status_code == 401


def test_auth_me_rejects_tampered_session_cookie(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    original_cookie = client.cookies.get("session")
    assert login.status_code == 200
    assert original_cookie is not None

    tampered_cookie = original_cookie[:-1] + ("0" if original_cookie[-1] != "0" else "1")
    client.cookies.set("session", tampered_cookie)
    me = client.get("/api/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "not authenticated"


def test_auth_revalidates_activity_and_role_from_repository(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200

    with repo._connect() as connection:
        connection.execute("update users set role = ? where username = ?", ("reviewer", "admin"))
        connection.commit()

    me_after_role_change = client.get("/api/auth/me")

    assert me_after_role_change.status_code == 200
    assert me_after_role_change.json()["user"]["role"] == "reviewer"

    with repo._connect() as connection:
        connection.execute("update users set active = 0 where username = ?", ("admin",))
        connection.commit()

    me_after_deactivation = client.get("/api/auth/me")
    second_me_after_deactivation = client.get("/api/auth/me")

    assert me_after_deactivation.status_code == 401
    assert me_after_deactivation.json()["detail"] == "not authenticated"
    assert "set-cookie" in me_after_deactivation.headers
    assert "session=null" in me_after_deactivation.headers["set-cookie"]
    assert second_me_after_deactivation.status_code == 401
    assert second_me_after_deactivation.json()["detail"] == "not authenticated"


def test_get_session_secret_requires_env_outside_pytest(monkeypatch):
    monkeypatch.delenv(manual_rating_auth.SESSION_SECRET_ENV_VAR, raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    with pytest.raises(RuntimeError, match="MANUAL_RATING_SESSION_SECRET"):
        manual_rating_auth.get_session_secret()


def test_bootstrap_manual_rating_admin_aborts_when_admin_exists(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "manual_rating.db"
    repo = ManualRatingRepository(db_path)
    repo.create_user(
        username="existing-admin",
        display_name="Existing Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "bootstrap-manual-rating-admin.py",
            "--username",
            "new-admin",
            "--display-name",
            "New Admin",
            "--password",
            "secret123",
            "--db-path",
            str(db_path),
        ],
    )

    with pytest.raises(SystemExit, match="admin user already exists"):
        runpy.run_path(
            str(Path(__file__).resolve().parents[2] / "scripts" / "bootstrap-manual-rating-admin.py"),
            run_name="__main__",
        )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert repo.find_user_by_username("new-admin") is None


def test_bootstrap_manual_rating_admin_works_when_invoked_from_elsewhere(tmp_path, monkeypatch, capsys):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap-manual-rating-admin.py"
    db_path = tmp_path / "manual_rating.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            str(script_path),
            "--username",
            "admin",
            "--display-name",
            "Admin",
            "--password",
            "secret123",
            "--db-path",
            str(db_path),
        ],
    )

    runpy.run_path(str(script_path), run_name="__main__")

    captured = capsys.readouterr()
    assert "created admin admin" in captured.out
    repo = ManualRatingRepository(db_path)
    created_user = repo.find_user_by_username("admin")
    assert created_user is not None
    assert created_user["role"] == "admin"


def test_admin_can_create_dataset_and_task_from_existing_images(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    admin = repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )
    reviewer = repo.create_user(
        username="reviewer",
        display_name="Reviewer",
        password_hash=hash_password("secret123"),
        role="reviewer",
    )
    monkeypatch.setattr(main, "repository", StubImageRepository([
        {"id": "img-1", "filename": "a.png", "experiment_group": "g1", "batch": "b1"},
        {"id": "img-2", "filename": "b.png", "experiment_group": "g1", "batch": "b1"},
    ]))

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    dataset = client.post(
        "/api/manual/datasets",
        json={
            "name": "Dataset A",
            "image_ids": ["img-1", "img-2"],
            "experiment_group": "g1",
            "batch": "b1",
        },
    )
    task = client.post(
        "/api/manual/tasks",
        json={
            "dataset_id": dataset.json()["dataset"]["id"],
            "name": "Task A",
            "description": "",
            "reviewer_ids": [reviewer["id"]],
        },
    )
    tasks = client.get("/api/manual/tasks")

    assert login.status_code == 200
    assert dataset.status_code == 200
    assert dataset.json()["dataset"]["created_by"] == admin["id"]
    assert dataset.json()["dataset"]["image_ids"] == ["img-1", "img-2"]
    assert task.status_code == 200
    assert task.json()["task"]["reviewer_count"] == 1
    assert task.json()["task"]["dataset_id"] == dataset.json()["dataset"]["id"]
    assert tasks.status_code == 200
    assert len(tasks.json()["tasks"]) == 1
    assert tasks.json()["tasks"][0]["dataset_name"] == "Dataset A"


def test_manual_admin_routes_require_admin_role(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="reviewer",
        display_name="Reviewer",
        password_hash=hash_password("secret123"),
        role="reviewer",
    )
    monkeypatch.setattr(main, "repository", StubImageRepository([
        {"id": "img-1", "filename": "a.png", "experiment_group": "g1", "batch": "b1"},
    ]))

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "reviewer", "password": "secret123"})
    create_dataset = client.post(
        "/api/manual/datasets",
        json={"name": "Dataset A", "image_ids": ["img-1"], "experiment_group": "g1", "batch": "b1"},
    )
    list_users = client.get("/api/manual/users")

    assert login.status_code == 200
    assert create_dataset.status_code == 403
    assert create_dataset.json()["detail"] == "admin required"
    assert list_users.status_code == 403
    assert list_users.json()["detail"] == "admin required"


def test_manual_users_hides_password_hash(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )
    repo.create_user(
        username="reviewer",
        display_name="Reviewer",
        password_hash=hash_password("secret123"),
        role="reviewer",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    response = client.get("/api/manual/users")

    assert login.status_code == 200
    assert response.status_code == 200
    assert [user["username"] for user in response.json()["users"]] == ["admin", "reviewer"]
    assert all("password_hash" not in user for user in response.json()["users"])


def test_reviewer_payload_is_blind_and_delete_is_blocked_for_referenced_images(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    client = context["client"]

    login = client.post("/api/auth/login", json={"username": "reviewer", "password": "secret123"})
    detail = client.get(f"/api/manual/tasks/{context['task_id']}/images/img-1")
    invalid = client.put(
        f"/api/manual/tasks/{context['task_id']}/images/img-1/rating",
        json={
            "sharpness_score": 7.3,
            "significance_score": 8.0,
            "artifact_suppression_score": 7.0,
            "structure_score": 8.5,
            "detail_score": 6.5,
            "comment": "",
        },
    )
    delete_attempt = client.delete("/api/images/img-1")

    assert login.status_code == 200
    assert detail.status_code == 200
    assert "metrics" not in detail.json()["image"]
    assert "overlay_urls" not in detail.json()["image"]
    assert "mask_url" not in detail.json()["image"]
    assert invalid.status_code == 422
    assert delete_attempt.status_code == 409
    assert delete_attempt.json()["detail"] == "image is referenced by a manual rating task"


def test_reviewer_rating_flow_updates_progress_and_admin_can_export(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    client = context["client"]

    reviewer_login = client.post("/api/auth/login", json={"username": "reviewer", "password": "secret123"})
    first_next = client.get(f"/api/manual/tasks/{context['task_id']}/next")
    put_rating = client.put(
        f"/api/manual/tasks/{context['task_id']}/images/img-1/rating",
        json={
            "sharpness_score": 7.5,
            "significance_score": 8.0,
            "artifact_suppression_score": 7.0,
            "structure_score": 8.5,
            "detail_score": 6.5,
            "comment": "ok",
        },
    )
    detail_after_rating = client.get(f"/api/manual/tasks/{context['task_id']}/images/img-1")
    second_next = client.get(f"/api/manual/tasks/{context['task_id']}/next")
    client.post("/api/auth/logout")

    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    summary = client.get(f"/api/manual/tasks/{context['task_id']}/summary")
    csv_export = client.get(f"/api/manual/tasks/{context['task_id']}/export/csv")
    excel_export = client.get(f"/api/manual/tasks/{context['task_id']}/export/excel")

    assert reviewer_login.status_code == 200
    assert first_next.status_code == 200
    assert first_next.json()["image_id"] == "img-1"
    assert put_rating.status_code == 200
    assert put_rating.json()["rating"]["comment"] == "ok"
    assert detail_after_rating.status_code == 200
    assert detail_after_rating.json()["image"]["progress"] == {"completed": 1, "total": 2}
    assert second_next.status_code == 200
    assert second_next.json()["image_id"] == "img-2"

    assert admin_login.status_code == 200
    assert summary.status_code == 200
    assert summary.json()["summary"]["rating_count"] == 1
    assert summary.json()["summary"]["rated_images"] == 1
    assert summary.json()["summary"]["progress"] == {"completed": 0, "total": 2}
    assert csv_export.status_code == 200
    assert "reviewer" in csv_export.text
    assert "img-1" in csv_export.text
    assert "7.5" in csv_export.text
    assert excel_export.status_code == 200
    assert excel_export.content[:2] == b"PK"
