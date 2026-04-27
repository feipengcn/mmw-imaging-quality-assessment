from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


EXPORT_COLUMNS = [
    "id",
    "filename",
    "experiment_group",
    "algorithm",
    "parameters",
    "batch",
    "quality_score",
    "subjective_rating",
    "subjective_rating_complete",
    "contour_clarity",
    "structure_integrity",
    "background_cleanliness",
    "artifact_acceptability",
    "practical_usability",
    "notes",
    "sharpness",
    "local_contrast",
    "snr",
    "structure_continuity",
    "artifact_strength",
    "body_area_ratio",
    "background_noise",
    "edge_density",
]


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        metrics = record.get("metrics") or {}
        subjective_scores = record.get("subjective_scores") or {}
        rows.append(
            {
                "id": record.get("id"),
                "filename": record.get("filename"),
                "experiment_group": record.get("experiment_group"),
                "algorithm": record.get("algorithm"),
                "parameters": record.get("parameters"),
                "batch": record.get("batch"),
                "quality_score": record.get("quality_score"),
                "subjective_rating": record.get("subjective_rating"),
                "subjective_rating_complete": record.get("subjective_rating_complete"),
                "contour_clarity": subjective_scores.get("contour_clarity"),
                "structure_integrity": subjective_scores.get("structure_integrity"),
                "background_cleanliness": subjective_scores.get("background_cleanliness"),
                "artifact_acceptability": subjective_scores.get("artifact_acceptability"),
                "practical_usability": subjective_scores.get("practical_usability"),
                "notes": record.get("notes"),
                **{metric: metrics.get(metric) for metric in EXPORT_COLUMNS if metric in metrics},
            }
        )
    return pd.DataFrame(rows, columns=EXPORT_COLUMNS)


def to_excel_bytes(records: list[dict[str, Any]]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        records_to_dataframe(records).to_excel(writer, index=False, sheet_name="quality_metrics")
    return buffer.getvalue()


def to_html_report(records: list[dict[str, Any]]) -> str:
    top = records[:5]
    bottom = records[-5:] if len(records) > 5 else []
    table_html = records_to_dataframe(records).to_html(index=False, classes="metrics", border=0)
    cards = "\n".join(_record_card(record) for record in top + bottom)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>毫米波人体成像质量评价报告</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1 {{ margin-bottom: 4px; }}
    .muted {{ color: #667085; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 24px 0; }}
    .card {{ border: 1px solid #d0d5dd; border-radius: 8px; padding: 12px; }}
    .score {{ font-size: 28px; font-weight: 700; }}
    table.metrics {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    table.metrics th, table.metrics td {{ border-bottom: 1px solid #eaecf0; padding: 8px; text-align: left; }}
  </style>
</head>
<body>
  <h1>毫米波人体成像质量评价报告</h1>
  <p class="muted">包含客观无参考指标、人工评分、加权总分和排序结果。</p>
  <div class="cards">{cards}</div>
  {table_html}
</body>
</html>"""


def _record_card(record: dict[str, Any]) -> str:
    return f"""
    <div class="card">
      <div class="score">{record.get("quality_score", 0):.2f}</div>
      <strong>{record.get("filename", "")}</strong>
      <p class="muted">{record.get("experiment_group", "")} / {record.get("algorithm", "")}</p>
    </div>
    """
