import sqlite3

import pytest

from app.manual_rating_repository import ManualRatingRepository


def test_repository_initializes_schema_and_upserts_ratings(tmp_path):
    repo = ManualRatingRepository(tmp_path / "manual_rating.db")
    with repo._connect() as connection:
        assert connection.execute("pragma foreign_keys").fetchone()[0] == 1

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
    other_reviewer = repo.create_user(
        username="other-reviewer",
        display_name="Other Reviewer",
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

    created = repo.upsert_rating(
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
    with repo._connect() as connection:
        row_count = connection.execute(
            """
            select count(*)
            from manual_ratings
            where task_id = ? and image_id = ? and reviewer_id = ?
            """,
            (task["id"], "img-1", reviewer["id"]),
        ).fetchone()[0]

    assert repo.find_user_by_username("admin")["role"] == "admin"
    assert repo.get_rating(task["id"], "img-1", reviewer["id"])["comment"] == "second"
    assert updated["id"] == created["id"]
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] != created["updated_at"]
    assert updated["sharpness_score"] == 8.0
    assert row_count == 1
    assert repo.image_is_referenced("img-1") is True
    with pytest.raises(sqlite3.IntegrityError):
        repo.create_task(
            dataset_id="missing-dataset",
            name="Broken Task",
            description="",
            reviewer_ids=[reviewer["id"]],
            created_by=admin["id"],
        )
    with pytest.raises(sqlite3.IntegrityError):
        repo.upsert_rating(
            task_id=task["id"],
            image_id="img-1",
            reviewer_id=other_reviewer["id"],
            scores={
                "sharpness_score": 7.0,
                "significance_score": 7.0,
                "artifact_suppression_score": 7.0,
                "structure_score": 7.0,
                "detail_score": 7.0,
            },
            comment="unassigned reviewer",
        )
    with pytest.raises(sqlite3.IntegrityError):
        repo.upsert_rating(
            task_id=task["id"],
            image_id="img-999",
            reviewer_id=reviewer["id"],
            scores={
                "sharpness_score": 7.0,
                "significance_score": 7.0,
                "artifact_suppression_score": 7.0,
                "structure_score": 7.0,
                "detail_score": 7.0,
            },
            comment="image not in dataset",
        )
