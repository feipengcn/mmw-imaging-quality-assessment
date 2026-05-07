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

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        password_hash: str,
        role: str,
        active: bool = True,
    ) -> dict[str, Any]:
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
                (
                    user["id"],
                    user["username"],
                    user["display_name"],
                    user["password_hash"],
                    user["role"],
                    user["active"],
                    user["created_at"],
                ),
            )
        return {**user, "active": bool(user["active"])}

    def find_user_by_username(self, username: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "select id, username, display_name, password_hash, role, active, created_at from users where username = ?",
                (username,),
            ).fetchone()
        user = self._row_to_dict(row)
        if user is None:
            return None
        user["active"] = bool(user["active"])
        return user

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
        dataset = {
            "id": uuid.uuid4().hex,
            "name": name,
            "source": source,
            "experiment_group": experiment_group,
            "batch": batch,
            "created_by": created_by,
            "created_at": self._timestamp(),
        }
        with self._connect() as connection:
            connection.execute(
                "insert into datasets (id, name, source, experiment_group, batch, created_by, created_at) values (?, ?, ?, ?, ?, ?, ?)",
                (
                    dataset["id"],
                    dataset["name"],
                    dataset["source"],
                    dataset["experiment_group"],
                    dataset["batch"],
                    dataset["created_by"],
                    dataset["created_at"],
                ),
            )
            connection.executemany(
                "insert into dataset_images (dataset_id, image_id, sort_order) values (?, ?, ?)",
                [
                    (dataset["id"], image_id, index)
                    for index, image_id in enumerate(image_ids)
                ],
            )
        return {**dataset, "image_ids": list(image_ids)}

    def create_task(
        self,
        *,
        dataset_id: str,
        name: str,
        description: str,
        reviewer_ids: list[str],
        created_by: str,
    ) -> dict[str, Any]:
        task = {
            "id": uuid.uuid4().hex,
            "dataset_id": dataset_id,
            "name": name,
            "description": description,
            "status": "draft",
            "created_by": created_by,
            "created_at": self._timestamp(),
        }
        with self._connect() as connection:
            connection.execute(
                "insert into rating_tasks (id, dataset_id, name, description, status, created_by, created_at) values (?, ?, ?, ?, ?, ?, ?)",
                (
                    task["id"],
                    task["dataset_id"],
                    task["name"],
                    task["description"],
                    task["status"],
                    task["created_by"],
                    task["created_at"],
                ),
            )
            connection.executemany(
                "insert into task_reviewers (task_id, reviewer_id, weight) values (?, ?, ?)",
                [(task["id"], reviewer_id, 1.0) for reviewer_id in reviewer_ids],
            )
        return {**task, "reviewer_ids": list(reviewer_ids)}

    def get_rating(self, task_id: str, image_id: str, reviewer_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                select id, task_id, image_id, reviewer_id, sharpness_score, significance_score,
                       artifact_suppression_score, structure_score, detail_score, comment,
                       created_at, updated_at
                from manual_ratings
                where task_id = ? and image_id = ? and reviewer_id = ?
                """,
                (task_id, image_id, reviewer_id),
            ).fetchone()
        return self._row_to_dict(row)

    def upsert_rating(
        self,
        *,
        task_id: str,
        image_id: str,
        reviewer_id: str,
        scores: dict[str, float],
        comment: str,
    ) -> dict[str, Any]:
        now = self._timestamp()
        rating_id = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                insert into manual_ratings (
                    id, task_id, image_id, reviewer_id, sharpness_score, significance_score,
                    artifact_suppression_score, structure_score, detail_score, comment, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(task_id, image_id, reviewer_id) do update set
                    sharpness_score = excluded.sharpness_score,
                    significance_score = excluded.significance_score,
                    artifact_suppression_score = excluded.artifact_suppression_score,
                    structure_score = excluded.structure_score,
                    detail_score = excluded.detail_score,
                    comment = excluded.comment,
                    updated_at = excluded.updated_at
                """,
                (
                    rating_id,
                    task_id,
                    image_id,
                    reviewer_id,
                    scores["sharpness_score"],
                    scores["significance_score"],
                    scores["artifact_suppression_score"],
                    scores["structure_score"],
                    scores["detail_score"],
                    comment,
                    now,
                    now,
                ),
            )
        rating = self.get_rating(task_id, image_id, reviewer_id)
        if rating is None:
            raise RuntimeError("rating was not persisted")
        return rating

    def image_is_referenced(self, image_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                select 1
                from dataset_images
                where image_id = ?
                union
                select 1
                from manual_ratings
                where image_id = ?
                limit 1
                """,
                (image_id, image_id),
            ).fetchone()
        return row is not None
