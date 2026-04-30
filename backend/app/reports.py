from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


EXPORT_COLUMNS = [
    "id",
    "filename",
    "view",
    "view_confidence",
    "experiment_group",
    "algorithm",
    "parameters",
    "batch",
    "valid_sample",
    "quality_score",
    "sharpness_score",
    "significance_score",
    "artifact_suppression_score",
    "structure_score",
    "detail_score",
    "tenengrad_variance",
    "edge_rise_distance",
    "cnr",
    "leakage_ratio",
    "background_bright_spot_ratio",
    "background_local_std",
    "component_count",
    "solidity",
    "saturation_ratio",
    "roi_entropy",
    "pai",
    "coherent_speckle_index",
    "body_area_ratio",
]


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        metrics = record.get("metrics") or {}
        normalized_metrics = record.get("normalized_metrics") or {}
        rows.append(
            {
                "id": record.get("id"),
                "filename": record.get("filename"),
                "view": record.get("view"),
                "view_confidence": record.get("view_confidence"),
                "experiment_group": record.get("experiment_group"),
                "algorithm": record.get("algorithm"),
                "parameters": record.get("parameters"),
                "batch": record.get("batch"),
                "valid_sample": record.get("valid_sample"),
                "quality_score": record.get("quality_score"),
                "sharpness_score": normalized_metrics.get("sharpness_score"),
                "significance_score": normalized_metrics.get("significance_score"),
                "artifact_suppression_score": normalized_metrics.get("artifact_suppression_score"),
                "structure_score": normalized_metrics.get("structure_score"),
                "detail_score": normalized_metrics.get("detail_score"),
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
  <p class="muted">包含毫米波专项物理指标、五维雷达分数、惩罚标记和总分排序结果。</p>
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
