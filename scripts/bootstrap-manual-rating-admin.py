from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.manual_rating_auth import hash_password
from backend.app.manual_rating_repository import ManualRatingRepository


def first_admin_username(repo: ManualRatingRepository) -> str | None:
    with repo._connect() as connection:
        existing_admin = connection.execute(
            "select username from users where role = ? limit 1",
            ("admin",),
        ).fetchone()
    return None if existing_admin is None else existing_admin["username"]


parser = argparse.ArgumentParser()
parser.add_argument("--username", required=True)
parser.add_argument("--display-name", required=True)
parser.add_argument("--password", required=True)
args = parser.parse_args()

repo = ManualRatingRepository(Path("data") / "manual_rating.db")
existing_admin_username = first_admin_username(repo)
if existing_admin_username is not None:
    raise SystemExit(f"admin user already exists: {existing_admin_username}")

repo.create_user(
    username=args.username,
    display_name=args.display_name,
    password_hash=hash_password(args.password),
    role="admin",
)
print(f"created admin {args.username}")
