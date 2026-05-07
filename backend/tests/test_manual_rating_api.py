from pathlib import Path
import runpy

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.manual_rating_auth import hash_password
from app.manual_rating_repository import ManualRatingRepository


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
    monkeypatch.setattr(main, "manual_rating_repository", repo)

    client = TestClient(main.app)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    me = client.get("/api/auth/me")
    inactive_login = client.post("/api/auth/login", json={"username": "inactive", "password": "secret123"})

    assert login.status_code == 200
    assert "set-cookie" in login.headers
    assert "session=" in login.headers["set-cookie"]
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "admin"
    assert inactive_login.status_code == 401
    assert inactive_login.json()["detail"] == "invalid credentials"


def test_bootstrap_manual_rating_admin_aborts_when_admin_exists(tmp_path, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    repo = ManualRatingRepository(data_dir / "manual_rating.db")
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
