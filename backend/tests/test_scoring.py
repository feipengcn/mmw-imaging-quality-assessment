from app.scoring import DEFAULT_WEIGHTS, score_records


def test_score_records_respects_metric_directions_and_weights():
    records = [
        {
            "id": "poor",
            "metrics": {
                "sharpness": 10,
                "local_contrast": 5,
                "snr": 1,
                "structure_continuity": 0.3,
                "artifact_strength": 40,
                "body_area_ratio": 0.1,
                "background_noise": 20,
            },
        },
        {
            "id": "good",
            "metrics": {
                "sharpness": 90,
                "local_contrast": 25,
                "snr": 8,
                "structure_continuity": 0.9,
                "artifact_strength": 5,
                "body_area_ratio": 0.3,
                "background_noise": 4,
            },
        },
    ]

    scored = score_records(records, DEFAULT_WEIGHTS)

    assert scored[0]["id"] == "good"
    assert scored[0]["quality_score"] > 95
    assert scored[1]["quality_score"] < 5


def test_subjective_rating_can_contribute_to_total_score():
    records = [
        {"id": "a", "metrics": {"sharpness": 10}, "subjective_rating": 5},
        {"id": "b", "metrics": {"sharpness": 90}, "subjective_rating": 1},
    ]
    weights = {"sharpness": 0.1, "subjective_rating": 0.9}

    scored = score_records(records, weights)

    assert scored[0]["id"] == "a"
    assert scored[0]["quality_score"] > scored[1]["quality_score"]
