from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.manual_rating_auth import hash_password
from backend.app.manual_rating_repository import ManualRatingRepository

DB_PATH_ENV_VAR = "MANUAL_RATING_DB_PATH"


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
parser.add_argument("--db-path", type=Path)
args = parser.parse_args()

db_path = (
    args.db_path
    if args.db_path is not None
    else Path(os.environ[DB_PATH_ENV_VAR]) if DB_PATH_ENV_VAR in os.environ
    else REPO_ROOT / "data" / "manual_rating.db"
)
repo = ManualRatingRepository(db_path)
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
