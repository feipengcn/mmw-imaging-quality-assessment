from pathlib import Path
import runpy
import sys

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import manual_rating_auth
from app.manual_rating_auth import hash_password
from app.manual_rating_repository import ManualRatingRepository


def _make_client(repo: ManualRatingRepository, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "manual_rating_repository", repo)
    main.app.state.manual_rating_repository = repo
    return TestClient(main.app)


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
