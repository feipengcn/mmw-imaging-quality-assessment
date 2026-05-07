# Manual Rating Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved multi-user manual rating module inside the existing app, with blind reviewer scoring, admin task assignment, SQLite-backed user/task/rating storage, and exportable results.

**Architecture:** Keep the existing FastAPI and React/Vite app as the only runtime. Add a dedicated SQLite-backed manual-rating repository plus auth/session endpoints on the backend, then add a separate manual-rating surface inside the existing frontend shell without introducing a new router dependency. Preserve the current automatic scoring workflow and reuse existing image IDs and upload URLs as the source of truth for manual-review tasks.

**Tech Stack:** FastAPI, Starlette session middleware, sqlite3, hashlib, pytest, React 19, TypeScript, Vitest, plain CSS

---

## File Structure

Primary backend files:

- Create: `backend/app/manual_rating_repository.py`
  Responsibility: SQLite schema initialization, user/task/dataset/rating CRUD, summary queries, export row queries, image reference checks
- Create: `backend/app/manual_rating_auth.py`
  Responsibility: password hashing, password verification, session helpers, current-user/admin guards
- Create: `backend/tests/test_manual_rating_repository.py`
  Responsibility: repository behavior coverage for users, datasets, tasks, ratings, summaries, and delete guards
- Create: `backend/tests/test_manual_rating_api.py`
  Responsibility: auth, permissions, task management, blind payloads, rating validation, and export behavior
- Create: `scripts/bootstrap-manual-rating-admin.py`
  Responsibility: create the first admin user in `data/manual_rating.db`
- Modify: `backend/app/main.py`
  Responsibility: repository wiring, session middleware, manual-rating API routes, delete-image guard, export endpoints

Primary frontend files:

- Create: `frontend/src/manualRatingTypes.ts`
  Responsibility: shared TypeScript types for auth, users, datasets, tasks, task detail, rating payloads, and summaries
- Create: `frontend/src/manualRatingApi.ts`
  Responsibility: browser API client for auth, admin, reviewer, and export requests
- Create: `frontend/src/manualRatingApi.test.ts`
  Responsibility: request/response and credentials handling for the manual-rating API client
- Create: `frontend/src/ManualRatingApp.tsx`
  Responsibility: manual-rating shell, login flow, role-based branch to admin or reviewer surfaces
- Create: `frontend/src/ManualRatingApp.test.tsx`
  Responsibility: UI regression coverage for login, admin task list, blind-review surface, and hidden automatic metrics
- Modify: `frontend/src/App.tsx`
  Responsibility: top-level mode switch between automatic analysis and manual-rating modules
- Modify: `frontend/src/styles.css`
  Responsibility: manual-rating layout, login page, admin workspace, blind-review workspace, and responsive rules

Keep the current automatic-analysis files and endpoints intact unless explicitly listed above.

## Shared Backend Data Shapes

Use dictionary-based payloads from the repository so the current codebase can stay lightweight and avoid introducing an ORM. The repository should expose these high-value methods:

```python
class ManualRatingRepository:
    def __init__(self, db_path: Path | str) -> None:
        raise NotImplementedError

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        password_hash: str,
        role: str,
        active: bool = True,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def list_users(self) -> list[dict[str, Any]]:
        raise NotImplementedError
    def update_user(self, user_id: str, **changes: Any) -> dict[str, Any]:
        raise NotImplementedError
    def find_user_by_username(self, username: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def create_dataset(
        self,
        *,
        name: str,
        source: str,
        experiment_group: str,
        batch: str,
        image_ids: list[str],
        created_by: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def list_datasets(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def create_task(
        self,
        *,
        dataset_id: str,
        name: str,
        description: str,
        reviewer_ids: list[str],
        created_by: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def list_tasks_for_user(self, user_id: str, role: str) -> list[dict[str, Any]]:
        raise NotImplementedError
    def get_task_detail(self, task_id: str, viewer_id: str, viewer_role: str) -> dict[str, Any]:
        raise NotImplementedError
    def next_image_for_reviewer(self, task_id: str, reviewer_id: str) -> str | None:
        raise NotImplementedError

    def upsert_rating(
        self,
        *,
        task_id: str,
        image_id: str,
        reviewer_id: str,
        scores: dict[str, float],
        comment: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_rating(self, task_id: str, image_id: str, reviewer_id: str) -> dict[str, Any] | None:
        raise NotImplementedError
    def task_summary(self, task_id: str) -> dict[str, Any]:
        raise NotImplementedError
    def export_rows(self, task_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError
    def image_is_referenced(self, image_id: str) -> bool:
        raise NotImplementedError
```

Keep auth simple and explicit:

```python
SESSION_USER_KEY = "manual_rating_user"

def hash_password(password: str) -> str:
    raise NotImplementedError
def verify_password(password: str, stored_hash: str) -> bool:
    raise NotImplementedError
def require_logged_in(request: Request) -> dict[str, Any]:
    raise NotImplementedError
def require_admin(request: Request) -> dict[str, Any]:
    raise NotImplementedError
```

## Shared Frontend Data Shapes

Manual-rating types should stay separate from `frontend/src/types.ts` to avoid polluting the automatic-analysis domain model.

```ts
export type ManualRole = 'admin' | 'reviewer';

export interface ManualUser {
  id: string;
  username: string;
  display_name: string;
  role: ManualRole;
  active: boolean;
}

export interface ManualTaskListItem {
  id: string;
  name: string;
  dataset_name: string;
  status: 'draft' | 'active' | 'closed';
  total_images: number;
  completed_images: number;
  reviewer_count: number;
}

export interface ReviewerImageDetail {
  task_id: string;
  image_id: string;
  filename: string;
  image_url: string;
  progress: {
    completed: number;
    total: number;
  };
  rating: ManualRatingForm | null;
}

export interface ManualRatingForm {
  sharpness_score: number;
  significance_score: number;
  artifact_suppression_score: number;
  structure_score: number;
  detail_score: number;
  comment: string;
}
```

The manual-rating UI should never consume `quality_score`, `metrics`, `overlay_urls`, or `mask_url`.

### Task 1: Add the SQLite repository foundation

**Files:**
- Create: `backend/app/manual_rating_repository.py`
- Test: `backend/tests/test_manual_rating_repository.py`

- [ ] **Step 1: Write the failing test**

Add a repository test that proves the SQLite schema is created, users can be inserted, and ratings upsert instead of duplicating rows.

```python
from app.manual_rating_repository import ManualRatingRepository


def test_repository_initializes_schema_and_upserts_ratings(tmp_path):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    admin = repo.create_user(
        username="admin",
        display_name="Admin",
        password_hash="hash",
        role="admin",
    )
    reviewer = repo.create_user(
        username="reviewer",
        display_name="Reviewer",
        password_hash="hash",
        role="reviewer",
    )
    dataset = repo.create_dataset(
        name="Batch A",
        source="existing_images",
        experiment_group="group-a",
        batch="batch-a",
        image_ids=["img-1", "img-2"],
        created_by=admin["id"],
    )
    task = repo.create_task(
        dataset_id=dataset["id"],
        name="Task A",
        description="",
        reviewer_ids=[reviewer["id"]],
        created_by=admin["id"],
    )

    repo.upsert_rating(
        task_id=task["id"],
        image_id="img-1",
        reviewer_id=reviewer["id"],
        scores={
            "sharpness_score": 7.5,
            "significance_score": 8.0,
            "artifact_suppression_score": 7.0,
            "structure_score": 8.5,
            "detail_score": 6.5,
        },
        comment="first",
    )
    updated = repo.upsert_rating(
        task_id=task["id"],
        image_id="img-1",
        reviewer_id=reviewer["id"],
        scores={
            "sharpness_score": 8.0,
            "significance_score": 8.0,
            "artifact_suppression_score": 7.0,
            "structure_score": 8.5,
            "detail_score": 6.5,
        },
        comment="second",
    )

    assert repo.find_user_by_username("admin")["role"] == "admin"
    assert repo.get_rating(task["id"], "img-1", reviewer["id"])["comment"] == "second"
    assert updated["sharpness_score"] == 8.0
    assert repo.image_is_referenced("img-1") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_manual_rating_repository.py -k upserts -v`

Expected: FAIL with `ModuleNotFoundError` or missing repository methods.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/manual_rating_repository.py` with schema setup, row helpers, and repository methods required by the test.

```python
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ManualRatingRepository:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists users (
                    id text primary key,
                    username text not null unique,
                    display_name text not null,
                    password_hash text not null,
                    role text not null,
                    active integer not null default 1,
                    created_at text not null
                );
                create table if not exists datasets (
                    id text primary key,
                    name text not null,
                    source text not null,
                    experiment_group text not null,
                    batch text not null,
                    created_by text not null,
                    created_at text not null
                );
                create table if not exists dataset_images (
                    dataset_id text not null,
                    image_id text not null,
                    sort_order integer not null,
                    unique(dataset_id, image_id)
                );
                create table if not exists rating_tasks (
                    id text primary key,
                    dataset_id text not null,
                    name text not null,
                    description text not null,
                    status text not null,
                    created_by text not null,
                    created_at text not null
                );
                create table if not exists task_reviewers (
                    task_id text not null,
                    reviewer_id text not null,
                    weight real not null default 1.0,
                    unique(task_id, reviewer_id)
                );
                create table if not exists manual_ratings (
                    id text primary key,
                    task_id text not null,
                    image_id text not null,
                    reviewer_id text not null,
                    sharpness_score real not null,
                    significance_score real not null,
                    artifact_suppression_score real not null,
                    structure_score real not null,
                    detail_score real not null,
                    comment text not null default '',
                    created_at text not null,
                    updated_at text not null,
                    unique(task_id, image_id, reviewer_id)
                );
                """
            )

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        return None if row is None else dict(row)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_user(self, *, username: str, display_name: str, password_hash: str, role: str, active: bool = True) -> dict[str, Any]:
        user = {
            "id": uuid.uuid4().hex,
            "username": username,
            "display_name": display_name,
            "password_hash": password_hash,
            "role": role,
            "active": 1 if active else 0,
            "created_at": self._timestamp(),
        }
        with self._connect() as connection:
            connection.execute(
                "insert into users (id, username, display_name, password_hash, role, active, created_at) values (?, ?, ?, ?, ?, ?, ?)",
                tuple(user.values()),
            )
        return {**user, "active": bool(user["active"])}
```

Also implement `find_user_by_username`, `create_dataset`, `create_task`, `get_rating`, `upsert_rating`, and `image_is_referenced` with explicit SQL.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_manual_rating_repository.py -k upserts -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/manual_rating_repository.py backend/tests/test_manual_rating_repository.py
git commit -m "feat: add manual rating repository foundation"
```

### Task 2: Add password hashing, sessions, and first-admin bootstrap

**Files:**
- Create: `backend/app/manual_rating_auth.py`
- Create: `scripts/bootstrap-manual-rating-admin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_manual_rating_api.py`

- [ ] **Step 1: Write the failing test**

Add an API test that proves login sets a session, `/api/auth/me` returns the current user, and inactive users cannot log in.

```python
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
    monkeypatch.setattr(main, "manual_rating_repository", repo)

    client = TestClient(main.app)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    me = client.get("/api/auth/me")

    assert login.status_code == 200
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "admin"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k session_and_me -v`

Expected: FAIL because the auth helpers and endpoints do not exist.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/manual_rating_auth.py` and wire it into `backend/app/main.py`.

```python
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from fastapi import HTTPException, Request

SESSION_USER_KEY = "manual_rating_user"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split(":", 1)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000)
    return hmac.compare_digest(actual, expected)


def require_logged_in(request: Request) -> dict[str, Any]:
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user
```

In `backend/app/main.py`, add session middleware and auth routes:

```python
from fastapi import Request
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from .manual_rating_auth import SESSION_USER_KEY, hash_password, require_admin, require_logged_in, verify_password
from .manual_rating_repository import ManualRatingRepository

app.add_middleware(SessionMiddleware, secret_key="mmw-manual-rating-dev-secret", same_site="lax")
manual_rating_repository = ManualRatingRepository(Path(__file__).resolve().parents[2] / "data" / "manual_rating.db")


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    user = manual_rating_repository.find_user_by_username(payload.username)
    if user is None or not user["active"] or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    session_user = {key: user[key] for key in ("id", "username", "display_name", "role", "active")}
    request.session[SESSION_USER_KEY] = session_user
    return {"user": session_user}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    return {"user": require_logged_in(request)}


@app.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}
```

Create `scripts/bootstrap-manual-rating-admin.py` so the first admin can be created without hand-editing the database:

```python
from pathlib import Path
import argparse

from backend.app.manual_rating_auth import hash_password
from backend.app.manual_rating_repository import ManualRatingRepository

parser = argparse.ArgumentParser()
parser.add_argument("--username", required=True)
parser.add_argument("--display-name", required=True)
parser.add_argument("--password", required=True)
args = parser.parse_args()

repo = ManualRatingRepository(Path("data") / "manual_rating.db")
repo.create_user(
    username=args.username,
    display_name=args.display_name,
    password_hash=hash_password(args.password),
    role="admin",
)
print(f"created admin {args.username}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k session_and_me -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/manual_rating_auth.py backend/app/main.py backend/tests/test_manual_rating_api.py scripts/bootstrap-manual-rating-admin.py
git commit -m "feat: add manual rating auth and session flow"
```

### Task 3: Add admin dataset and task management APIs

**Files:**
- Modify: `backend/app/manual_rating_repository.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_manual_rating_api.py`

- [ ] **Step 1: Write the failing test**

Add an API test proving an admin can create a dataset from existing image IDs and create a task assigned to reviewers.

```python
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
    monkeypatch.setattr(main, "manual_rating_repository", repo)
    monkeypatch.setattr(
        main,
        "repository",
        StubImageRepository(
            [
                {"id": "img-1", "filename": "a.png", "experiment_group": "g1", "batch": "b1"},
                {"id": "img-2", "filename": "b.png", "experiment_group": "g1", "batch": "b1"},
            ]
        ),
    )

    client = TestClient(main.app)
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    dataset = client.post("/api/manual/datasets", json={
        "name": "Dataset A",
        "image_ids": ["img-1", "img-2"],
        "experiment_group": "g1",
        "batch": "b1",
    })
    task = client.post("/api/manual/tasks", json={
        "dataset_id": dataset.json()["dataset"]["id"],
        "name": "Task A",
        "description": "",
        "reviewer_ids": [reviewer["id"]],
    })

    assert dataset.status_code == 200
    assert task.status_code == 200
    assert task.json()["task"]["reviewer_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k create_dataset_and_task -v`

Expected: FAIL because the admin manual-rating routes do not exist.

- [ ] **Step 3: Write minimal implementation**

Add request models and admin endpoints to `backend/app/main.py`:

```python
class CreateDatasetRequest(BaseModel):
    name: str
    image_ids: list[str]
    experiment_group: str = ""
    batch: str = ""


class CreateTaskRequest(BaseModel):
    dataset_id: str
    name: str
    description: str = ""
    reviewer_ids: list[str]


@app.get("/api/manual/users")
def manual_users(request: Request) -> dict[str, Any]:
    require_admin(request)
    users = manual_rating_repository.list_users()
    sanitized = [{key: value for key, value in user.items() if key != "password_hash"} for user in users]
    return {"users": sanitized}


@app.post("/api/manual/datasets")
def create_manual_dataset(request: Request, payload: CreateDatasetRequest) -> dict[str, Any]:
    admin = require_admin(request)
    dataset = manual_rating_repository.create_dataset(
        name=payload.name,
        source="existing_images",
        experiment_group=payload.experiment_group,
        batch=payload.batch,
        image_ids=payload.image_ids,
        created_by=admin["id"],
    )
    return {"dataset": dataset}


@app.post("/api/manual/tasks")
def create_manual_task(request: Request, payload: CreateTaskRequest) -> dict[str, Any]:
    admin = require_admin(request)
    task = manual_rating_repository.create_task(
        dataset_id=payload.dataset_id,
        name=payload.name,
        description=payload.description,
        reviewer_ids=payload.reviewer_ids,
        created_by=admin["id"],
    )
    return {"task": task}


@app.get("/api/manual/tasks")
def list_manual_tasks(request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    return {"tasks": manual_rating_repository.list_tasks_for_user(user["id"], user["role"])}
```

Extend the repository with `list_users`, `create_dataset`, `list_datasets`, `create_task`, and `list_tasks_for_user`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k create_dataset_and_task -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/manual_rating_repository.py backend/app/main.py backend/tests/test_manual_rating_api.py
git commit -m "feat: add admin manual rating task management"
```

### Task 4: Add reviewer blind-rating APIs, summaries, exports, and image delete protection

**Files:**
- Modify: `backend/app/manual_rating_repository.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_manual_rating_api.py`

- [ ] **Step 1: Write the failing test**

Add an API test proving the reviewer image payload is blind, score validation enforces `0.5` steps, and deleting a referenced image is blocked.

```python
def test_reviewer_payload_is_blind_and_delete_is_blocked_for_referenced_images(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    client = context["client"]

    client.post("/api/auth/login", json={"username": "reviewer", "password": "secret123"})
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

    assert detail.status_code == 200
    assert "metrics" not in detail.json()["image"]
    assert "overlay_urls" not in detail.json()["image"]
    assert invalid.status_code == 422
    assert delete_attempt.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k blind_and_delete -v`

Expected: FAIL because the reviewer routes and delete guard do not exist.

- [ ] **Step 3: Write minimal implementation**

Add rating request models and reviewer endpoints:

```python
class ManualRatingRequest(BaseModel):
    sharpness_score: float
    significance_score: float
    artifact_suppression_score: float
    structure_score: float
    detail_score: float
    comment: str = ""


def _validate_manual_rating(payload: ManualRatingRequest) -> dict[str, float]:
    scores = {
        "sharpness_score": payload.sharpness_score,
        "significance_score": payload.significance_score,
        "artifact_suppression_score": payload.artifact_suppression_score,
        "structure_score": payload.structure_score,
        "detail_score": payload.detail_score,
    }
    for value in scores.values():
        if value < 0 or value > 10 or round(value * 2) != value * 2:
            raise HTTPException(status_code=422, detail="scores must be 0-10 in 0.5 increments")
    return scores


@app.get("/api/manual/tasks/{task_id}/next")
def next_manual_image(task_id: str, request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    image_id = manual_rating_repository.next_image_for_reviewer(task_id, user["id"])
    return {"image_id": image_id}


@app.get("/api/manual/tasks/{task_id}/images/{image_id}")
def manual_image_detail(task_id: str, image_id: str, request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    detail = manual_rating_repository.get_task_detail(task_id, user["id"], user["role"])
    rating = manual_rating_repository.get_rating(task_id, image_id, user["id"])
    image = next(item for item in repository.list_records() if item["id"] == image_id)
    return {
        "image": {
            "task_id": task_id,
            "image_id": image_id,
            "filename": image["filename"],
            "image_url": f"/uploads/{image_id}",
            "progress": detail["progress"],
            "rating": rating,
        }
    }


@app.put("/api/manual/tasks/{task_id}/images/{image_id}/rating")
def put_manual_rating(task_id: str, image_id: str, payload: ManualRatingRequest, request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    rating = manual_rating_repository.upsert_rating(
        task_id=task_id,
        image_id=image_id,
        reviewer_id=user["id"],
        scores=_validate_manual_rating(payload),
        comment=payload.comment,
    )
    return {"rating": rating}
```

Add task summary and export endpoints with explicit implementations:

```python
@app.get("/api/manual/tasks/{task_id}/summary")
def manual_task_summary(task_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"summary": manual_rating_repository.task_summary(task_id)}


@app.get("/api/manual/tasks/{task_id}/export/csv")
def manual_task_export_csv(task_id: str, request: Request) -> StreamingResponse:
    require_admin(request)
    rows = manual_rating_repository.export_rows(task_id)
    csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=manual-rating-{task_id}.csv"},
    )


@app.get("/api/manual/tasks/{task_id}/export/excel")
def manual_task_export_excel(task_id: str, request: Request) -> Response:
    require_admin(request)
    rows = manual_rating_repository.export_rows(task_id)
    output = io.BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=manual-rating-{task_id}.xlsx"},
    )
```

Protect image deletion in `delete_image()`:

```python
if manual_rating_repository.image_is_referenced(image_id):
    raise HTTPException(status_code=409, detail="image is referenced by a manual rating task")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k blind_and_delete -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/manual_rating_repository.py backend/app/main.py backend/tests/test_manual_rating_api.py
git commit -m "feat: add blind review rating and export endpoints"
```

### Task 5: Add manual-rating frontend types and API client

**Files:**
- Create: `frontend/src/manualRatingTypes.ts`
- Create: `frontend/src/manualRatingApi.ts`
- Create: `frontend/src/manualRatingApi.test.ts`

- [ ] **Step 1: Write the failing test**

Add an API client test proving auth requests send JSON and reviewer/admin fetches include credentials.

```ts
import { describe, expect, it, vi } from 'vitest';
import { fetchManualTasks, loginManualUser } from './manualRatingApi';

describe('manual rating api', () => {
  it('logs in and fetches tasks with credentials', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ user: { id: 'u1', username: 'admin', display_name: 'Admin', role: 'admin', active: true } }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ tasks: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    await loginManualUser('admin', 'secret123');
    await fetchManualTasks();

    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/api/auth/login', expect.objectContaining({ method: 'POST' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/api/manual/tasks', expect.objectContaining({ credentials: 'include' }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- src/manualRatingApi.test.ts`

Expected: FAIL because the manual-rating API client does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/manualRatingTypes.ts` and `frontend/src/manualRatingApi.ts`.

```ts
import type {
  ManualTaskListItem,
  ManualUser,
  ReviewerImageDetail,
  ManualRatingForm,
} from './manualRatingTypes';

const jsonHeaders = { 'Content-Type': 'application/json' };

async function ensureOk<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function loginManualUser(username: string, password: string): Promise<{ user: ManualUser }> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: jsonHeaders,
    credentials: 'include',
    body: JSON.stringify({ username, password }),
  });
  return ensureOk(response);
}

export async function fetchCurrentManualUser(): Promise<{ user: ManualUser }> {
  const response = await fetch('/api/auth/me', { credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualTasks(): Promise<{ tasks: ManualTaskListItem[] }> {
  const response = await fetch('/api/manual/tasks', { credentials: 'include' });
  return ensureOk(response);
}
```

Also implement `logoutManualUser`, `createManualUser`, `createManualDataset`, `createManualTask`, `fetchManualTaskDetail`, `fetchReviewerImageDetail`, and `submitManualRating`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend -- src/manualRatingApi.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/manualRatingTypes.ts frontend/src/manualRatingApi.ts frontend/src/manualRatingApi.test.ts
git commit -m "feat: add manual rating frontend api client"
```

### Task 6: Add the manual-rating shell and login flow to the frontend

**Files:**
- Create: `frontend/src/ManualRatingApp.tsx`
- Create: `frontend/src/ManualRatingApp.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing test**

Add a UI test proving the top bar can switch to the manual-rating module and shows a login form when no reviewer/admin session exists.

```tsx
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('manual rating shell', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('switches into manual rating mode and shows a login form', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      if (input === '/api/auth/me') {
        return Promise.resolve(new Response('not authenticated', { status: 401 }));
      }
      return Promise.resolve(
        new Response(JSON.stringify({ images: [], weights: {} }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });

    const root = document.createElement('div');
    document.body.appendChild(root);

    await act(async () => {
      createRoot(root).render(<App />);
    });

    const manualButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('人工评分'),
    );
    await act(async () => {
      manualButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.body.textContent).toContain('用户名');
    expect(document.body.textContent).toContain('密码');
    expect(document.body.textContent).not.toContain('质量雷达图');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "shows a login form"`

Expected: FAIL because the manual-rating shell and mode switch do not exist.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/ManualRatingApp.tsx` with local auth state and a login form.

```tsx
import { FormEvent, useEffect, useState } from 'react';

import { fetchCurrentManualUser, loginManualUser } from './manualRatingApi';
import type { ManualUser } from './manualRatingTypes';

function ManualRatingApp() {
  const [user, setUser] = useState<ManualUser | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCurrentManualUser().then((payload) => setUser(payload.user)).catch(() => setUser(null));
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    try {
      const payload = await loginManualUser(username, password);
      setUser(payload.user);
      setPassword('');
    } catch {
      setError('登录失败');
    }
  }

  if (!user) {
    return (
      <section className="manual-login-shell">
        <form className="manual-login-form" onSubmit={handleLogin}>
          <h2>人工评分登录</h2>
          <label>
            用户名
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            密码
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error ? <p>{error}</p> : null}
          <button type="submit">登录</button>
        </form>
      </section>
    );
  }

  return <section className="manual-rating-shell">{user.display_name}</section>;
}

export default ManualRatingApp;
```

Modify `frontend/src/App.tsx` to switch modes without adding a router dependency:

```tsx
type WorkspaceMode = 'analysis' | 'manual-rating';

const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>('analysis');

<div className="topbar-mode-switch" role="tablist" aria-label="工作模式">
  <button type="button" className={workspaceMode === 'analysis' ? 'active' : ''} onClick={() => setWorkspaceMode('analysis')}>
    自动评估
  </button>
  <button type="button" className={workspaceMode === 'manual-rating' ? 'active' : ''} onClick={() => setWorkspaceMode('manual-rating')}>
    人工评分
  </button>
</div>

if (workspaceMode === 'manual-rating') {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>毫米波人体成像质量评估</h1>
          <p>面向 mmWave 图像的物理指标评分与样本排序</p>
        </div>
        <div className="topbar-actions">
          <div className="topbar-mode-switch" role="tablist" aria-label="工作模式">
            <button type="button" onClick={() => setWorkspaceMode('analysis')}>
              自动评估
            </button>
            <button type="button" className="active" onClick={() => setWorkspaceMode('manual-rating')}>
              人工评分
            </button>
          </div>
        </div>
      </header>
      <ManualRatingApp />
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "shows a login form"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ManualRatingApp.tsx frontend/src/ManualRatingApp.test.tsx frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat: add manual rating shell and login page"
```

### Task 7: Add the admin dashboard for users, datasets, tasks, and summaries

**Files:**
- Modify: `frontend/src/ManualRatingApp.tsx`
- Modify: `frontend/src/ManualRatingApp.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing test**

Add a UI test proving an admin session sees task creation and user-management controls.

```tsx
it('shows admin task and user controls after login', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (input === '/api/auth/me') {
      return Promise.resolve(
        new Response(JSON.stringify({ user: { id: 'u1', username: 'admin', display_name: 'Admin', role: 'admin', active: true } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks') {
      return Promise.resolve(
        new Response(JSON.stringify({ tasks: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/users') {
      return Promise.resolve(
        new Response(JSON.stringify({ users: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/datasets') {
      return Promise.resolve(
        new Response(JSON.stringify({ datasets: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    return Promise.resolve(new Response('[]', { status: 200 }));
  });

  const root = document.createElement('div');
  document.body.appendChild(root);

  await act(async () => {
    createRoot(root).render(<ManualRatingApp />);
  });

  expect(document.body.textContent).toContain('创建任务');
  expect(document.body.textContent).toContain('创建用户');
  expect(document.body.textContent).toContain('任务列表');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "shows admin task and user controls"`

Expected: FAIL because the logged-in admin UI is still a placeholder.

- [ ] **Step 3: Write minimal implementation**

Extend `frontend/src/ManualRatingApp.tsx` with an admin branch that loads tasks, users, and datasets.

```tsx
function AdminWorkspace({ user }: { user: ManualUser }) {
  const [tasks, setTasks] = useState<ManualTaskListItem[]>([]);
  const [users, setUsers] = useState<ManualUser[]>([]);
  const [datasets, setDatasets] = useState<ManualDataset[]>([]);

  useEffect(() => {
    fetchManualTasks().then((payload) => setTasks(payload.tasks));
    fetchManualUsers().then((payload) => setUsers(payload.users));
    fetchManualDatasets().then((payload) => setDatasets(payload.datasets));
  }, []);

  return (
    <div className="manual-admin-layout">
      <section className="manual-panel">
        <h2>任务列表</h2>
        {tasks.map((task) => (
          <button type="button" key={task.id} className="manual-task-row">
            <strong>{task.name}</strong>
            <span>{task.dataset_name}</span>
          </button>
        ))}
      </section>
      <section className="manual-panel">
        <h2>创建任务</h2>
        <button type="button">创建任务</button>
        <h2>创建用户</h2>
        <button type="button">创建用户</button>
      </section>
    </div>
  );
}
```

Render it from `ManualRatingApp`:

```tsx
if (user.role === 'admin') {
  return <AdminWorkspace user={user} />;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "shows admin task and user controls"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ManualRatingApp.tsx frontend/src/ManualRatingApp.test.tsx frontend/src/styles.css
git commit -m "feat: add manual rating admin dashboard"
```

### Task 8: Add the reviewer blind-rating workspace

**Files:**
- Modify: `frontend/src/ManualRatingApp.tsx`
- Modify: `frontend/src/ManualRatingApp.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing test**

Add a UI test proving the reviewer sees only the raw image and the five score inputs, not automatic metrics or overlays.

```tsx
it('shows a blind-review workspace for reviewers', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (input === '/api/auth/me') {
      return Promise.resolve(
        new Response(JSON.stringify({ user: { id: 'u2', username: 'reviewer', display_name: 'Reviewer', role: 'reviewer', active: true } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks') {
      return Promise.resolve(
        new Response(JSON.stringify({ tasks: [{ id: 'task-1', name: 'Task A', dataset_name: 'Dataset A', status: 'active', total_images: 10, completed_images: 2, reviewer_count: 2 }] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks/task-1/images/img-1') {
      return Promise.resolve(
        new Response(JSON.stringify({ image: { task_id: 'task-1', image_id: 'img-1', filename: 'a.png', image_url: '/uploads/img-1', progress: { completed: 2, total: 10 }, rating: null } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks/task-1/next') {
      return Promise.resolve(
        new Response(JSON.stringify({ image_id: 'img-1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    return Promise.resolve(new Response('[]', { status: 200 }));
  });

  const root = document.createElement('div');
  document.body.appendChild(root);

  await act(async () => {
    createRoot(root).render(<ManualRatingApp />);
  });

  expect(document.body.textContent).toContain('清晰度');
  expect(document.body.textContent).toContain('显著性');
  expect(document.body.textContent).toContain('伪影抑制');
  expect(document.body.textContent).not.toContain('质量雷达图');
  expect(document.body.textContent).not.toContain('AOI');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "blind-review workspace"`

Expected: FAIL because the reviewer workspace does not exist.

- [ ] **Step 3: Write minimal implementation**

Extend `ManualRatingApp.tsx` with a reviewer branch.

```tsx
function createEmptyRating(): ManualRatingForm {
  return {
    sharpness_score: 5,
    significance_score: 5,
    artifact_suppression_score: 5,
    structure_score: 5,
    detail_score: 5,
    comment: '',
  };
}

function ReviewerWorkspace({ user }: { user: ManualUser }) {
  const [tasks, setTasks] = useState<ManualTaskListItem[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [image, setImage] = useState<ReviewerImageDetail | null>(null);
  const [form, setForm] = useState<ManualRatingForm>(createEmptyRating());

  useEffect(() => {
    fetchManualTasks().then((payload) => {
      setTasks(payload.tasks);
      const firstTask = payload.tasks[0];
      if (firstTask) {
        setActiveTaskId(firstTask.id);
      }
    });
  }, []);

  useEffect(() => {
    if (!activeTaskId) return;
    fetchNextReviewerImage(activeTaskId).then((payload) => {
      if (!payload.image_id) return;
      fetchReviewerImageDetail(activeTaskId, payload.image_id).then((detail) => {
        setImage(detail.image);
        setForm(detail.image.rating ?? createEmptyRating());
      });
    });
  }, [activeTaskId]);

  return (
    <div className="manual-review-layout">
      <aside className="manual-task-sidebar">
        <h2>我的任务</h2>
        {tasks.map((task) => (
          <button type="button" key={task.id} onClick={() => setActiveTaskId(task.id)}>
            {task.name}
          </button>
        ))}
      </aside>
      <section className="manual-review-stage">
        {image ? <img src={image.image_url} alt={image.filename} className="manual-review-image" /> : null}
      </section>
      <form className="manual-rating-form">
        <label>清晰度<input type="number" min="0" max="10" step="0.5" value={form.sharpness_score} /></label>
        <label>显著性<input type="number" min="0" max="10" step="0.5" value={form.significance_score} /></label>
        <label>伪影抑制<input type="number" min="0" max="10" step="0.5" value={form.artifact_suppression_score} /></label>
        <label>结构完整性<input type="number" min="0" max="10" step="0.5" value={form.structure_score} /></label>
        <label>细节保真度<input type="number" min="0" max="10" step="0.5" value={form.detail_score} /></label>
        <button type="submit">保存并下一张</button>
      </form>
    </div>
  );
}
```

Render it from `ManualRatingApp`:

```tsx
return <ReviewerWorkspace user={user} />;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "blind-review workspace"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ManualRatingApp.tsx frontend/src/ManualRatingApp.test.tsx frontend/src/styles.css
git commit -m "feat: add blind review workspace"
```

### Task 9: Wire end-to-end task actions, run full verification, and finish

**Files:**
- Modify: `frontend/src/ManualRatingApp.tsx`
- Modify: `backend/tests/test_manual_rating_api.py`
- Modify: `frontend/src/ManualRatingApp.test.tsx`
- Modify: `README.md`

- [ ] **Step 1: Write the failing tests**

Add one backend test for CSV export rows and one frontend test for successful submit-and-next behavior.

```python
def test_task_export_contains_reviewer_scores_and_average_columns(tmp_path, monkeypatch):
    context = build_manual_rating_context(tmp_path, monkeypatch)
    client = context["client"]
    client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    response = client.get(f"/api/manual/tasks/{task_id}/export/csv")
    assert response.status_code == 200
    assert "sharpness_score" in response.text
    assert "sharpness_average" in response.text
```

```tsx
it('submits reviewer scores and moves to the next image', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    if (input === '/api/auth/me') {
      return Promise.resolve(
        new Response(JSON.stringify({ user: { id: 'u2', username: 'reviewer', display_name: 'Reviewer', role: 'reviewer', active: true } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks') {
      return Promise.resolve(
        new Response(JSON.stringify({ tasks: [{ id: 'task-1', name: 'Task A', dataset_name: 'Dataset A', status: 'active', total_images: 2, completed_images: 0, reviewer_count: 1 }] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks/task-1/next') {
      return Promise.resolve(
        new Response(JSON.stringify({ image_id: nextImageIds.shift() ?? null }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks/task-1/images/img-1') {
      return Promise.resolve(
        new Response(JSON.stringify({ image: { task_id: 'task-1', image_id: 'img-1', filename: 'a.png', image_url: '/uploads/img-1', progress: { completed: 0, total: 2 }, rating: null } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks/task-1/images/img-2') {
      return Promise.resolve(
        new Response(JSON.stringify({ image: { task_id: 'task-1', image_id: 'img-2', filename: 'b.png', image_url: '/uploads/img-2', progress: { completed: 1, total: 2 }, rating: null } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    if (input === '/api/manual/tasks/task-1/images/img-1/rating' && init?.method === 'PUT') {
      return Promise.resolve(
        new Response(JSON.stringify({ rating: { image_id: 'img-1', sharpness_score: 7.5 } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    return Promise.resolve(new Response('[]', { status: 200 }));
  });

  const nextImageIds = ['img-1', 'img-2'];
  const root = document.createElement('div');
  document.body.appendChild(root);

  await act(async () => {
    createRoot(root).render(<ManualRatingApp />);
  });

  const submitButton = Array.from(document.querySelectorAll('button')).find((button) =>
    button.textContent?.includes('保存并下一张'),
  );
  expect(submitButton).toBeTruthy();

  await act(async () => {
    submitButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });

  expect(document.body.textContent).toContain('b.png');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_manual_rating_api.py -k export_contains -v`

Expected: FAIL

Run: `npm test --prefix frontend -- src/ManualRatingApp.test.tsx -t "submits reviewer scores and moves to the next image"`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Finish the remaining wiring:

```tsx
async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  if (!activeTaskId || !image) return;
  await submitManualRating(activeTaskId, image.image_id, form);
  const next = await fetchNextReviewerImage(activeTaskId);
  if (!next.image_id) {
    setImage(null);
    return;
  }
  const detail = await fetchReviewerImageDetail(activeTaskId, next.image_id);
  setImage(detail.image);
  setForm(detail.image.rating ?? createEmptyRating());
}
```

Add a short README section showing how to bootstrap the first admin and where the SQLite file lives:

```md
## Manual Rating Module

Bootstrap the first admin user:

```powershell
python .\scripts\bootstrap-manual-rating-admin.py --username admin --display-name 管理员 --password secret123
```

Runtime data:

- SQLite: `data/manual_rating.db`
- Image source: existing `data/uploads/` and `data/state.json`
```

- [ ] **Step 4: Run full verification**

Run: `python -m pytest`

Expected: PASS with the new manual-rating backend tests included.

Run: `npm test --prefix frontend`

Expected: PASS with the new manual-rating frontend tests included.

Run: `npm run build --prefix frontend`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_manual_rating_api.py frontend/src/ManualRatingApp.tsx frontend/src/ManualRatingApp.test.tsx README.md
git commit -m "feat: complete manual rating workflow"
```

## Self-Review Checklist

- Spec coverage:
  Auth, users, datasets, task assignment, blind reviewer payloads, `0.5` step validation, summaries, exports, frontend mode switch, admin dashboard, reviewer workspace, and image delete protection each have a dedicated task above.
- Placeholder scan:
  No deferred implementation markers or shorthand placeholders should remain in the plan.
- Type consistency:
  Repository methods, auth helpers, and frontend type names stay consistent across tasks. Preserve `ManualUser`, `ManualTaskListItem`, `ReviewerImageDetail`, and `ManualRatingForm` naming when implementing.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-07-manual-rating-module.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
