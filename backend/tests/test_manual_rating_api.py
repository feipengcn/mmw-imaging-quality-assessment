from pathlib import Path
import runpy
import sys
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

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


def _png_bytes(color: int = 128) -> bytes:
    buffer = io.BytesIO()
    Image.new("L", (4, 4), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


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


def test_auth_bootstrap_status_reports_when_first_admin_is_needed(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    client = _make_client(repo, monkeypatch)

    before = client.get("/api/auth/bootstrap-status")

    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    after = client.get("/api/auth/bootstrap-status")

    assert before.status_code == 200
    assert before.json() == {"needs_setup": True}
    assert after.status_code == 200
    assert after.json() == {"needs_setup": False}


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


def test_admin_can_create_manual_user(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    response = client.post(
        "/api/manual/users",
        json={
            "username": "reviewer-2",
            "display_name": "Reviewer Two",
            "password": "secret123",
            "role": "reviewer",
            "active": True,
        },
    )

    assert login.status_code == 200
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "reviewer-2"
    assert response.json()["user"]["role"] == "reviewer"
    assert "password_hash" not in response.json()["user"]
    assert repo.find_user_by_username("reviewer-2") is not None


def test_admin_can_upload_files_and_create_dataset_directly(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    client = _make_client(repo, monkeypatch)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    response = client.post(
        "/api/manual/datasets/upload",
        data={"name": "人工评分数据集"},
        files=[
            ("files", ("folder-a/a.png", _png_bytes(96), "image/png")),
            ("files", ("folder-a/b.png", _png_bytes(144), "image/png")),
        ],
    )
    datasets = client.get("/api/manual/datasets")

    assert login.status_code == 200
    assert response.status_code == 200
    assert response.json()["dataset"]["name"] == "人工评分数据集"
    assert response.json()["dataset"]["source"] == "folder-a"
    assert len(response.json()["dataset"]["image_ids"]) == 2
    assert datasets.status_code == 200
    assert datasets.json()["datasets"][0]["source"] == "folder-a"


def test_admin_can_upload_folder_dataset_with_optional_labels(tmp_path, monkeypatch):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash=hash_password("secret123"),
        role="admin",
    )

    client = _make_client(repo, monkeypatch)
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    response = client.post(
        "/api/manual/datasets/upload",
        data={
            "name": "文件夹导入数据集",
            "source_label": "现场采集",
            "batch_label": "2026-05-07 晚班",
            "note_label": "",
        },
        files=[
            ("files", ("session-1/front/a.png", _png_bytes(96), "image/png")),
            ("files", ("session-1/front/b.png", _png_bytes(144), "image/png")),
        ],
    )
    datasets = client.get("/api/manual/datasets")

    assert response.status_code == 200
    payload = response.json()["dataset"]
    assert payload["name"] == "文件夹导入数据集"
    assert payload["source"] == "session-1/front"
    assert payload["source_label"] == "现场采集"
    assert payload["batch_label"] == "2026-05-07 晚班"
    assert payload["note_label"] == ""
    assert payload["image_count"] == 2
    assert datasets.status_code == 200
    assert datasets.json()["datasets"][0]["source_label"] == "现场采集"
    assert datasets.json()["datasets"][0]["batch_label"] == "2026-05-07 晚班"


def test_admin_task_summary_includes_reviewer_progress(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    repo = context["repo"]
    second_reviewer = repo.create_user(
        username="reviewer-2",
        display_name="Reviewer Two",
        password_hash=hash_password("secret123"),
        role="reviewer",
    )
    with repo._connect() as connection:
        connection.execute(
            "insert into task_reviewers (task_id, reviewer_id, weight) values (?, ?, ?)",
            (context["task_id"], second_reviewer["id"], 1.5),
        )
        connection.commit()

    client = context["client"]
    client.post("/api/auth/login", json={"username": "reviewer", "password": "secret123"})
    client.put(
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
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "reviewer-2", "password": "secret123"})
    client.put(
        f"/api/manual/tasks/{context['task_id']}/images/img-1/rating",
        json={
            "sharpness_score": 5.0,
            "significance_score": 6.0,
            "artifact_suppression_score": 5.5,
            "structure_score": 6.5,
            "detail_score": 5.0,
            "comment": "needs work",
        },
    )
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})

    summary = client.get(f"/api/manual/tasks/{context['task_id']}/summary")

    assert summary.status_code == 200
    reviewer_progress = summary.json()["summary"]["reviewer_progress"]
    assert len(reviewer_progress) == 2
    assert reviewer_progress[0]["reviewer_display_name"] == "Reviewer"
    assert reviewer_progress[0]["completed_images"] == 1
    assert reviewer_progress[0]["total_images"] == 2
    assert reviewer_progress[1]["reviewer_display_name"] == "Reviewer Two"
    assert reviewer_progress[1]["completed_images"] == 1
    assert reviewer_progress[1]["weight"] == 1.5


def test_admin_can_view_single_image_multi_reviewer_scores_and_aggregates(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    repo = context["repo"]
    second_reviewer = repo.create_user(
        username="reviewer-2",
        display_name="Reviewer Two",
        password_hash=hash_password("secret123"),
        role="reviewer",
    )
    with repo._connect() as connection:
        connection.execute(
            "insert into task_reviewers (task_id, reviewer_id, weight) values (?, ?, ?)",
            (context["task_id"], second_reviewer["id"], 2.0),
        )
        connection.commit()
    repo.upsert_rating(
        task_id=context["task_id"],
        image_id="img-1",
        reviewer_id=context["reviewer"]["id"],
        scores={
            "sharpness_score": 8.0,
            "significance_score": 8.0,
            "artifact_suppression_score": 7.0,
            "structure_score": 9.0,
            "detail_score": 6.0,
        },
        comment="first",
    )
    repo.upsert_rating(
        task_id=context["task_id"],
        image_id="img-1",
        reviewer_id=second_reviewer["id"],
        scores={
            "sharpness_score": 5.0,
            "significance_score": 6.0,
            "artifact_suppression_score": 5.0,
            "structure_score": 6.0,
            "detail_score": 4.0,
        },
        comment="second",
    )

    client = context["client"]
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    response = client.get(f"/api/manual/tasks/{context['task_id']}/images/img-1/admin-detail")

    assert response.status_code == 200
    detail = response.json()["image"]
    assert detail["image_id"] == "img-1"
    assert detail["filename"] == "a.png"
    assert len(detail["ratings"]) == 2
    assert detail["ratings"][0]["reviewer_display_name"] == "Reviewer"
    assert detail["ratings"][1]["reviewer_display_name"] == "Reviewer Two"
    assert detail["aggregates"]["average"]["sharpness_score"] == 6.5
    assert detail["aggregates"]["weighted"]["sharpness_score"] == pytest.approx(6.0)
    assert detail["aggregates"]["weighted"]["overall_score"] == pytest.approx((7.6 + 2 * 5.2) / 3, rel=1e-3)


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


def test_reviewer_can_list_task_images_with_own_scores_only(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    repo = context["repo"]
    repo.upsert_rating(
        task_id=context["task_id"],
        image_id="img-1",
        reviewer_id=context["reviewer"]["id"],
        scores={
            "sharpness_score": 7.5,
            "significance_score": 8.0,
            "artifact_suppression_score": 7.0,
            "structure_score": 8.5,
            "detail_score": 6.5,
        },
        comment="ok",
    )
    client = context["client"]
    client.post("/api/auth/login", json={"username": "reviewer", "password": "secret123"})

    response = client.get(f"/api/manual/tasks/{context['task_id']}/images")

    assert response.status_code == 200
    images = response.json()["images"]
    assert [image["filename"] for image in images] == ["a.png", "b.png"]
    assert images[0]["rating"]["comment"] == "ok"
    assert images[0]["overall_score"] == 7.5
    assert images[1]["rating"] is None
    assert images[1]["overall_score"] is None
    assert "aggregates" not in images[0]


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
