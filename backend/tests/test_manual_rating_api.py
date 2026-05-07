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
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "admin"
    assert inactive_login.status_code == 401
    assert inactive_login.json()["detail"] == "invalid credentials"
