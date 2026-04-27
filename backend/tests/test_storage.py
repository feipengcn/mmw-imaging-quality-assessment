from io import BytesIO

import numpy as np
from PIL import Image

from app.storage import ImageRepository


def test_import_files_preserves_folder_relative_display_path(tmp_path):
    arr = np.full((32, 32), 20, dtype=np.uint8)
    arr[8:24, 10:22] = 200
    buffer = BytesIO()
    Image.fromarray(arr, mode="L").save(buffer, format="PNG")

    repo = ImageRepository(tmp_path)
    imported = repo.import_files(
        [("case-a/algorithm-1/sample.png", buffer.getvalue())],
        experiment_group="group",
        algorithm="algorithm-1",
        parameters="p",
        batch="b",
    )

    assert imported[0]["filename"] == "case-a/algorithm-1/sample.png"


def test_update_rating_stores_dimension_scores_and_average(tmp_path):
    arr = np.full((32, 32), 20, dtype=np.uint8)
    arr[8:24, 10:22] = 200
    buffer = BytesIO()
    Image.fromarray(arr, mode="L").save(buffer, format="PNG")

    repo = ImageRepository(tmp_path)
    image_id = repo.import_files(
        [("sample.png", buffer.getvalue())],
        experiment_group="group",
        algorithm="algorithm-1",
        parameters="p",
        batch="b",
    )[0]["id"]

    updated = repo.update_rating(
        image_id,
        subjective_scores={
            "contour_clarity": 5,
            "structure_integrity": 4,
            "background_cleanliness": 3,
            "artifact_acceptability": 4,
            "practical_usability": 5,
        },
        notes="usable image",
    )

    assert updated["subjective_rating"] == 4.2
    assert updated["subjective_scores"]["contour_clarity"] == 5
    assert updated["subjective_rating_complete"] is True
    assert updated["notes"] == "usable image"
