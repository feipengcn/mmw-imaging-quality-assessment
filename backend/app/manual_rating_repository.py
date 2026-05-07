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
        connection.execute("pragma foreign_keys = on")
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
                    created_at text not null,
                    foreign key (created_by) references users(id)
                );
                create table if not exists dataset_images (
                    dataset_id text not null,
                    image_id text not null,
                    sort_order integer not null,
                    unique(dataset_id, image_id),
                    foreign key (dataset_id) references datasets(id)
                );
                create table if not exists rating_tasks (
                    id text primary key,
                    dataset_id text not null,
                    name text not null,
                    description text not null,
                    status text not null,
                    created_by text not null,
                    created_at text not null,
                    foreign key (dataset_id) references datasets(id),
                    foreign key (created_by) references users(id)
                );
                create table if not exists task_reviewers (
                    task_id text not null,
                    reviewer_id text not null,
                    weight real not null default 1.0,
                    unique(task_id, reviewer_id),
                    foreign key (task_id) references rating_tasks(id),
                    foreign key (reviewer_id) references users(id)
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
                    unique(task_id, image_id, reviewer_id),
                    foreign key (task_id) references rating_tasks(id),
                    foreign key (reviewer_id) references users(id)
                );
                create index if not exists idx_dataset_images_image_id on dataset_images(image_id);
                create index if not exists idx_manual_ratings_image_id on manual_ratings(image_id);
                create trigger if not exists manual_ratings_validate_insert
                before insert on manual_ratings
                for each row
                begin
                    select
                        case
                            when not exists (
                                select 1
                                from task_reviewers
                                where task_id = new.task_id and reviewer_id = new.reviewer_id
                            ) then raise(abort, 'manual rating reviewer must be assigned to task')
                        end;
                    select
                        case
                            when not exists (
                                select 1
                                from rating_tasks
                                join dataset_images on dataset_images.dataset_id = rating_tasks.dataset_id
                                where rating_tasks.id = new.task_id and dataset_images.image_id = new.image_id
                            ) then raise(abort, 'manual rating image must belong to task dataset')
                        end;
                end;
                create trigger if not exists manual_ratings_validate_update
                before update on manual_ratings
                for each row
                begin
                    select
                        case
                            when not exists (
                                select 1
                                from task_reviewers
                                where task_id = new.task_id and reviewer_id = new.reviewer_id
                            ) then raise(abort, 'manual rating reviewer must be assigned to task')
                        end;
                    select
                        case
                            when not exists (
                                select 1
                                from rating_tasks
                                join dataset_images on dataset_images.dataset_id = rating_tasks.dataset_id
                                where rating_tasks.id = new.task_id and dataset_images.image_id = new.image_id
                            ) then raise(abort, 'manual rating image must belong to task dataset')
                        end;
                end;
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

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select id, username, display_name, password_hash, role, active, created_at
                from users
                order by created_at asc
                """
            ).fetchall()
        users = [dict(row) for row in rows]
        for user in users:
            user["active"] = bool(user["active"])
        return users

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
        return {
            **task,
            "reviewer_ids": list(reviewer_ids),
            "reviewer_count": len(reviewer_ids),
        }

    def list_datasets(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            dataset_rows = connection.execute(
                """
                select id, name, source, experiment_group, batch, created_by, created_at
                from datasets
                order by created_at desc
                """
            ).fetchall()
            image_rows = connection.execute(
                """
                select dataset_id, image_id
                from dataset_images
                order by sort_order asc
                """
            ).fetchall()
        image_ids_by_dataset: dict[str, list[str]] = {}
        for row in image_rows:
            image_ids_by_dataset.setdefault(row["dataset_id"], []).append(row["image_id"])
        return [
            {**dict(row), "image_ids": image_ids_by_dataset.get(row["id"], [])}
            for row in dataset_rows
        ]

    def list_tasks_for_user(self, user_id: str, role: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if role == "admin":
                rows = connection.execute(
                    """
                    select
                        rating_tasks.id,
                        rating_tasks.dataset_id,
                        rating_tasks.name,
                        rating_tasks.description,
                        rating_tasks.status,
                        rating_tasks.created_by,
                        rating_tasks.created_at,
                        datasets.name as dataset_name,
                        count(distinct dataset_images.image_id) as total_images,
                        count(distinct task_reviewers.reviewer_id) as reviewer_count
                    from rating_tasks
                    join datasets on datasets.id = rating_tasks.dataset_id
                    left join dataset_images on dataset_images.dataset_id = datasets.id
                    left join task_reviewers on task_reviewers.task_id = rating_tasks.id
                    group by rating_tasks.id
                    order by rating_tasks.created_at desc
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    select
                        rating_tasks.id,
                        rating_tasks.dataset_id,
                        rating_tasks.name,
                        rating_tasks.description,
                        rating_tasks.status,
                        rating_tasks.created_by,
                        rating_tasks.created_at,
                        datasets.name as dataset_name,
                        count(distinct dataset_images.image_id) as total_images,
                        count(distinct task_reviewers.reviewer_id) as reviewer_count
                    from rating_tasks
                    join task_reviewers on task_reviewers.task_id = rating_tasks.id
                    join datasets on datasets.id = rating_tasks.dataset_id
                    left join dataset_images on dataset_images.dataset_id = datasets.id
                    where task_reviewers.reviewer_id = ?
                    group by rating_tasks.id
                    order by rating_tasks.created_at desc
                    """,
                    (user_id,),
                ).fetchall()

            completed_rows = connection.execute(
                """
                select task_id, reviewer_id, count(distinct image_id) as completed_images
                from manual_ratings
                group by task_id, reviewer_id
                """
            ).fetchall()

        completed_by_task: dict[str, int] = {}
        for row in completed_rows:
            completed_by_task[row["task_id"]] = completed_by_task.get(row["task_id"], 0) + int(row["completed_images"])

        tasks = []
        for row in rows:
            task = dict(row)
            task["total_images"] = int(task["total_images"])
            task["reviewer_count"] = int(task["reviewer_count"])
            task["completed_images"] = completed_by_task.get(task["id"], 0)
            tasks.append(task)
        return tasks

    def next_image_for_reviewer(self, task_id: str, reviewer_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                select dataset_images.image_id
                from rating_tasks
                join dataset_images on dataset_images.dataset_id = rating_tasks.dataset_id
                left join manual_ratings
                    on manual_ratings.task_id = rating_tasks.id
                   and manual_ratings.image_id = dataset_images.image_id
                   and manual_ratings.reviewer_id = ?
                where rating_tasks.id = ? and manual_ratings.id is null
                order by dataset_images.sort_order asc
                limit 1
                """,
                (reviewer_id, task_id),
            ).fetchone()
        return None if row is None else row["image_id"]

    def get_task_detail(self, task_id: str, viewer_id: str, viewer_role: str) -> dict[str, Any]:
        with self._connect() as connection:
            task_row = connection.execute(
                """
                select rating_tasks.id, rating_tasks.dataset_id, rating_tasks.name, rating_tasks.description,
                       rating_tasks.status, rating_tasks.created_by, rating_tasks.created_at,
                       datasets.name as dataset_name
                from rating_tasks
                join datasets on datasets.id = rating_tasks.dataset_id
                where rating_tasks.id = ?
                """,
                (task_id,),
            ).fetchone()
            if task_row is None:
                raise KeyError(task_id)

            reviewer_row = connection.execute(
                """
                select 1
                from task_reviewers
                where task_id = ? and reviewer_id = ?
                """,
                (task_id, viewer_id),
            ).fetchone()
            if viewer_role != "admin" and reviewer_row is None:
                raise PermissionError(task_id)

            total_images = connection.execute(
                """
                select count(*)
                from dataset_images
                where dataset_id = ?
                """,
                (task_row["dataset_id"],),
            ).fetchone()[0]
            completed_images = connection.execute(
                """
                select count(distinct image_id)
                from manual_ratings
                where task_id = ? and reviewer_id = ?
                """,
                (task_id, viewer_id),
            ).fetchone()[0]

        detail = dict(task_row)
        detail["progress"] = {
            "completed": int(completed_images),
            "total": int(total_images),
        }
        return detail

    def task_summary(self, task_id: str) -> dict[str, Any]:
        detail = self.get_task_detail(task_id, "", "admin")
        with self._connect() as connection:
            row = connection.execute(
                """
                select count(*) as rating_count,
                       count(distinct reviewer_id) as reviewer_count,
                       count(distinct image_id) as rated_images
                from manual_ratings
                where task_id = ?
                """,
                (task_id,),
            ).fetchone()
        return {
            "task_id": task_id,
            "task_name": detail["name"],
            "dataset_name": detail["dataset_name"],
            "progress": detail["progress"],
            "rating_count": int(row["rating_count"]),
            "reviewer_count": int(row["reviewer_count"]),
            "rated_images": int(row["rated_images"]),
        }

    def export_rows(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select
                    manual_ratings.task_id,
                    manual_ratings.image_id,
                    dataset_images.sort_order,
                    users.username as reviewer_username,
                    users.display_name as reviewer_display_name,
                    manual_ratings.sharpness_score,
                    manual_ratings.significance_score,
                    manual_ratings.artifact_suppression_score,
                    manual_ratings.structure_score,
                    manual_ratings.detail_score,
                    manual_ratings.comment,
                    manual_ratings.created_at,
                    manual_ratings.updated_at
                from manual_ratings
                join users on users.id = manual_ratings.reviewer_id
                join rating_tasks on rating_tasks.id = manual_ratings.task_id
                join dataset_images
                    on dataset_images.dataset_id = rating_tasks.dataset_id
                   and dataset_images.image_id = manual_ratings.image_id
                where manual_ratings.task_id = ?
                order by dataset_images.sort_order asc, users.username asc
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

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
