from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from .reports import records_to_dataframe, to_excel_bytes, to_html_report
from .scoring import DEFAULT_WEIGHTS, normalize_weights, score_records
from .storage import ImageRepository


app = FastAPI(title="MMW Imaging Quality Assessment", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = ImageRepository(Path(__file__).resolve().parents[2] / "data")


class ScoreRequest(BaseModel):
    weights: dict[str, float] | None = None


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
    try:
        repository.delete_image(image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="image not found") from exc
    records = score_records(repository.list_records(), DEFAULT_WEIGHTS)
    return {"images": _with_asset_urls(records), "weights": DEFAULT_WEIGHTS}


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
