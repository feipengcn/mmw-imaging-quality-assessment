from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
import pandas as pd
from pydantic import BaseModel

from .manual_rating_auth import (
    SESSION_USER_KEY,
    SignedSessionMiddleware,
    configure_user_lookup,
    get_session_secret,
    require_admin,
    require_logged_in,
    verify_password,
)
from .manual_rating_repository import ManualRatingRepository
from .reports import records_to_dataframe, to_excel_bytes, to_html_report
from .scoring import DEFAULT_WEIGHTS, normalize_weights, score_records
from .storage import ImageRepository


app = FastAPI(title="MMW Imaging Quality Assessment", version="0.1.0")
app.add_middleware(
    SignedSessionMiddleware,
    secret_key=get_session_secret(),
    same_site="lax",
    https_only=os.environ.get("MANUAL_RATING_SESSION_HTTPS_ONLY") == "1",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = ImageRepository(Path(__file__).resolve().parents[2] / "data")
manual_rating_repository = ManualRatingRepository(Path(__file__).resolve().parents[2] / "data" / "manual_rating.db")
app.state.manual_rating_repository = manual_rating_repository
configure_user_lookup(manual_rating_repository.find_user_by_username)


class ScoreRequest(BaseModel):
    weights: dict[str, float] | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


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


class ManualRatingRequest(BaseModel):
    sharpness_score: float
    significance_score: float
    artifact_suppression_score: float
    structure_score: float
    detail_score: float
    comment: str = ""


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/weights")
def weights() -> dict[str, dict[str, float]]:
    return {"weights": DEFAULT_WEIGHTS}


@app.get("/api/images")
def list_images() -> dict[str, Any]:
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    return {"images": _with_asset_urls(records), "weights": DEFAULT_WEIGHTS}


@app.post("/api/images/score")
def score_images(request: ScoreRequest) -> dict[str, Any]:
    weights = normalize_weights(request.weights)
    records = score_records(repository.list_records(), weights)
    return {"images": _with_asset_urls(records), "weights": weights}


@app.post("/api/import")
async def import_images(
    files: Annotated[list[UploadFile], File()],
    experiment_group: Annotated[str, Form()] = "default",
    algorithm: Annotated[str, Form()] = "unknown",
    parameters: Annotated[str, Form()] = "",
    batch: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    payload: list[tuple[str, bytes]] = []
    for upload in files:
        payload.append((upload.filename or "image", await upload.read()))
    imported = repository.import_files(payload, experiment_group, algorithm, parameters, batch)
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    return {"imported": len(imported), "images": _with_asset_urls(records)}


@app.post("/api/import/progress")
async def import_images_with_progress(
    files: Annotated[list[UploadFile], File()],
    experiment_group: Annotated[str, Form()] = "default",
    algorithm: Annotated[str, Form()] = "unknown",
    parameters: Annotated[str, Form()] = "",
    batch: Annotated[str, Form()] = "",
) -> StreamingResponse:
    payload: list[tuple[str, bytes]] = []
    for upload in files:
        payload.append((upload.filename or "image", await upload.read()))

    def events():
        imported_count = 0
        for progress in repository.iter_import_files(payload, experiment_group, algorithm, parameters, batch):
            imported_count += 1
            record = progress["record"]
            yield json.dumps(
                {
                    "type": "progress",
                    "completed": progress["completed"],
                    "total": progress["total"],
                    "filename": record["filename"],
                },
                ensure_ascii=False,
            ) + "\n"

        records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
        yield json.dumps(
            {
                "type": "complete",
                "imported": imported_count,
                "images": _with_asset_urls(records),
                "weights": DEFAULT_WEIGHTS,
            },
            ensure_ascii=False,
        ) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.get("/uploads/{image_id}")
def get_image(image_id: str) -> FileResponse:
    return _file_response(repository.image_path(image_id))


@app.get("/masks/{image_id}")
def get_mask(image_id: str) -> FileResponse:
    return _file_response(repository.mask_path(image_id))


@app.get("/overlays/{image_id}/{kind}")
def get_overlay(image_id: str, kind: str) -> FileResponse:
    try:
        return _file_response(repository.overlay_path(image_id, kind))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="overlay not found") from exc


@app.get("/api/export/csv")
def export_csv() -> StreamingResponse:
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    csv_bytes = records_to_dataframe(records).to_csv(index=False).encode("utf-8-sig")
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mmw_quality_metrics.csv"},
    )


@app.get("/api/export/excel")
def export_excel() -> Response:
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    return Response(
        content=to_excel_bytes(records),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=mmw_quality_metrics.xlsx"},
    )


@app.get("/api/report/html")
def html_report() -> HTMLResponse:
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    return HTMLResponse(to_html_report(records))


@app.delete("/api/images")
def reset_images() -> dict[str, list[Any]]:
    repository.reset()
    return {"images": []}


@app.delete("/api/images/{image_id}")
def delete_image(image_id: str) -> dict[str, Any]:
    if manual_rating_repository.image_is_referenced(image_id):
        raise HTTPException(status_code=409, detail="image is referenced by a manual rating task")
    try:
        repository.delete_image(image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="image not found") from exc
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    return {"images": _with_asset_urls(records), "weights": DEFAULT_WEIGHTS}


@app.post("/api/auth/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    user = manual_rating_repository.find_user_by_username(payload.username)
    if user is None or not user["active"] or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    session_user = {
        key: user[key]
        for key in ("id", "username", "display_name", "role", "active")
    }
    request.session[SESSION_USER_KEY] = {"username": user["username"]}
    return {"user": session_user}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    return {"user": require_logged_in(request)}


@app.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/manual/users")
def manual_users(request: Request) -> dict[str, Any]:
    require_admin(request)
    users = manual_rating_repository.list_users()
    return {
        "users": [
            {key: value for key, value in user.items() if key != "password_hash"}
            for user in users
        ]
    }


@app.get("/api/manual/datasets")
def list_manual_datasets(request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"datasets": manual_rating_repository.list_datasets()}


@app.post("/api/manual/datasets")
def create_manual_dataset(request: Request, payload: CreateDatasetRequest) -> dict[str, Any]:
    admin = require_admin(request)
    existing_records = {record["id"]: record for record in repository.list_records()}
    for image_id in payload.image_ids:
        if image_id not in existing_records:
            raise HTTPException(status_code=400, detail=f"unknown image id: {image_id}")

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


@app.get("/api/manual/tasks/{task_id}/next")
def next_manual_image(task_id: str, request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    return {"image_id": manual_rating_repository.next_image_for_reviewer(task_id, user["id"])}


@app.get("/api/manual/tasks/{task_id}/images/{image_id}")
def manual_image_detail(task_id: str, image_id: str, request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    try:
        detail = manual_rating_repository.get_task_detail(task_id, user["id"], user["role"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="task access denied") from exc
    image = next((item for item in repository.list_records() if item["id"] == image_id), None)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    rating = manual_rating_repository.get_rating(task_id, image_id, user["id"])
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
def put_manual_rating(
    task_id: str,
    image_id: str,
    payload: ManualRatingRequest,
    request: Request,
) -> dict[str, Any]:
    user = require_logged_in(request)
    scores = _validate_manual_rating(payload)
    try:
        rating = manual_rating_repository.upsert_rating(
            task_id=task_id,
            image_id=image_id,
            reviewer_id=user["id"],
            scores=scores,
            comment=payload.comment,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=403, detail="rating access denied") from exc
    return {"rating": rating}


@app.get("/api/manual/tasks/{task_id}/summary")
def manual_task_summary(task_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        summary = manual_rating_repository.task_summary(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc
    return {"summary": summary}


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
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(manual_rating_repository.export_rows(task_id)).to_excel(
            writer,
            index=False,
            sheet_name="manual_ratings",
        )
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=manual-rating-{task_id}.xlsx"},
    )


def _with_asset_urls(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for record in records:
        item = json.loads(json.dumps(record, ensure_ascii=False))
        item["image_url"] = f"/uploads/{record['id']}"
        item["mask_url"] = f"/masks/{record['id']}"
        item["overlay_urls"] = {
            "aoi": f"/overlays/{record['id']}/aoi",
            "leakage": f"/overlays/{record['id']}/leakage",
            "stripe": f"/overlays/{record['id']}/stripe",
        }
        enriched.append(item)
    return enriched


def _file_response(path: Path) -> FileResponse:
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


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
