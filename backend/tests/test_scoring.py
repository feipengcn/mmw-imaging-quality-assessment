from app.scoring import DEFAULT_WEIGHTS, QUALITY_DIMENSIONS, score_records


def build_record(record_id: str, **metrics: float):
    return {
        "id": record_id,
        "metrics": metrics,
    }


def test_score_records_use_anchor_normalization_and_mmwave_dimensions():
    records = [
        build_record(
            "strong",
            tenengrad_variance=6.2e9,
            edge_rise_distance=2.2,
            cnr=180.0,
            leakage_ratio=8.0,
            background_bright_spot_ratio=0.003,
            background_local_std=0.18,
            component_count=2,
            solidity=0.36,
            saturation_ratio=0.0,
            roi_entropy=7.62,
            pai=3.9,
            coherent_speckle_index=0.18,
            body_area_ratio=0.18,
        ),
        build_record(
            "weak",
            tenengrad_variance=7.5e8,
            edge_rise_distance=7.8,
            cnr=12.0,
            leakage_ratio=45.0,
            background_bright_spot_ratio=0.03,
            background_local_std=4.8,
            component_count=4,
            solidity=0.3,
            saturation_ratio=0.08,
            roi_entropy=7.3,
            pai=6.5,
            coherent_speckle_index=0.31,
            body_area_ratio=0.19,
        ),
    ]

    scored = score_records(records, DEFAULT_WEIGHTS)

    assert scored[0]["id"] == "strong"
    assert set(QUALITY_DIMENSIONS).issubset(scored[0]["normalized_metrics"].keys())
    assert "cnr" in scored[0]["metric_scores"]
    assert scored[0]["metric_score_max"] == 100
    assert scored[0]["quality_score"] > 70
    assert scored[1]["quality_score"] < 45


def test_low_is_better_metrics_are_converted_into_higher_scores():
    scored = score_records(
        [
            build_record(
                "clean",
                tenengrad_variance=2.0e9,
                edge_rise_distance=2.6,
                cnr=40.0,
                leakage_ratio=2.0,
                background_bright_spot_ratio=0.002,
                background_local_std=0.2,
                component_count=1,
                solidity=0.44,
                saturation_ratio=0.0,
                roi_entropy=7.55,
                pai=3.5,
                coherent_speckle_index=0.16,
                body_area_ratio=0.18,
            ),
            build_record(
                "dirty",
                tenengrad_variance=2.0e9,
                edge_rise_distance=7.5,
                cnr=40.0,
                leakage_ratio=50.0,
                background_bright_spot_ratio=0.022,
                background_local_std=4.8,
                component_count=4,
                solidity=0.32,
                saturation_ratio=0.05,
                roi_entropy=7.55,
                pai=5.9,
                coherent_speckle_index=0.3,
                body_area_ratio=0.18,
            ),
        ],
        DEFAULT_WEIGHTS,
    )

    clean = next(record for record in scored if record["id"] == "clean")
    dirty = next(record for record in scored if record["id"] == "dirty")

    assert clean["metric_scores"]["leakage_ratio"] > dirty["metric_scores"]["leakage_ratio"]
    assert clean["metric_scores"]["background_bright_spot_ratio"] > dirty["metric_scores"]["background_bright_spot_ratio"]
    assert clean["metric_scores"]["background_local_std"] > dirty["metric_scores"]["background_local_std"]
    assert clean["metric_scores"]["edge_rise_distance"] > dirty["metric_scores"]["edge_rise_distance"]
    assert clean["metric_scores"]["coherent_speckle_index"] > dirty["metric_scores"]["coherent_speckle_index"]


def test_saturation_and_pai_trigger_large_penalty():
    scored = score_records(
        [
            build_record(
                "clean",
                tenengrad_variance=5.0e9,
                edge_rise_distance=2.5,
                cnr=120.0,
                leakage_ratio=6.0,
                background_bright_spot_ratio=0.0,
                background_local_std=0.3,
                component_count=1,
                solidity=0.42,
                saturation_ratio=0.0,
                roi_entropy=7.6,
                pai=3.2,
                coherent_speckle_index=0.16,
                body_area_ratio=0.18,
            ),
            build_record(
                "saturated",
                tenengrad_variance=5.0e9,
                edge_rise_distance=2.5,
                cnr=120.0,
                leakage_ratio=6.0,
                background_bright_spot_ratio=0.01,
                background_local_std=0.3,
                component_count=1,
                solidity=0.42,
                saturation_ratio=0.22,
                roi_entropy=7.6,
                pai=6.5,
                coherent_speckle_index=0.12,
                body_area_ratio=0.18,
            ),
        ],
        DEFAULT_WEIGHTS,
    )

    clean = next(record for record in scored if record["id"] == "clean")
    saturated = next(record for record in scored if record["id"] == "saturated")

    assert saturated["penalty_flags"]["saturation"] is True
    assert saturated["penalty_flags"]["pai"] is True
    assert saturated["quality_score"] < clean["quality_score"] * 0.5


def test_too_small_body_area_marks_invalid_sample():
    scored = score_records(
        [
            build_record(
                "invalid",
                tenengrad_variance=2.0e9,
                edge_rise_distance=3.0,
                cnr=30.0,
                leakage_ratio=4.0,
                background_bright_spot_ratio=0.0,
                background_local_std=0.3,
                component_count=1,
                solidity=0.42,
                saturation_ratio=0.0,
                roi_entropy=7.55,
                pai=3.4,
                coherent_speckle_index=0.16,
                body_area_ratio=0.03,
            )
        ],
        DEFAULT_WEIGHTS,
    )

    assert scored[0]["valid_sample"] is False
    assert scored[0]["quality_score"] <= 20


def test_view_specific_profiles_allow_front_structure_and_back_leakage_tolerance():
    scored = score_records(
        [
            {
                **build_record(
                    "front_case",
                    tenengrad_variance=2.0e9,
                    edge_rise_distance=3.0,
                    cnr=40.0,
                    leakage_ratio=20.0,
                    background_bright_spot_ratio=0.01,
                    background_local_std=1.6,
                    component_count=2,
                    solidity=0.48,
                    saturation_ratio=0.0,
                    roi_entropy=7.55,
                    pai=3.5,
                    coherent_speckle_index=0.16,
                    body_area_ratio=0.18,
                ),
                "view": "front",
            },
            {
                **build_record(
                    "back_case",
                    tenengrad_variance=2.0e9,
                    edge_rise_distance=3.0,
                    cnr=40.0,
                    leakage_ratio=20.0,
                    background_bright_spot_ratio=0.01,
                    background_local_std=1.6,
                    component_count=2,
                    solidity=0.48,
                    saturation_ratio=0.0,
                    roi_entropy=7.55,
                    pai=3.5,
                    coherent_speckle_index=0.16,
                    body_area_ratio=0.18,
                ),
                "view": "back",
            },
        ],
        DEFAULT_WEIGHTS,
    )

    front = next(record for record in scored if record["id"] == "front_case")
    back = next(record for record in scored if record["id"] == "back_case")

    assert front["metric_scores"]["component_count"] > back["metric_scores"]["component_count"]
    assert back["metric_scores"]["solidity"] > front["metric_scores"]["solidity"]
    assert back["metric_scores"]["leakage_ratio"] > front["metric_scores"]["leakage_ratio"]


def test_typical_ranking_calibration_prefers_1_then_4_then_3():
    scored = score_records(
        [
            build_record(
                "typical_1",
                tenengrad_variance=6232526599.6415,
                edge_rise_distance=2.3014,
                cnr=197.1219,
                leakage_ratio=103.9746,
                background_bright_spot_ratio=0.0049,
                background_local_std=0.1401,
                component_count=2.0,
                solidity=0.3393,
                saturation_ratio=0.0,
                roi_entropy=7.6017,
                pai=3.9734,
                coherent_speckle_index=0.1913,
                body_area_ratio=0.1555,
            ),
            build_record(
                "typical_2",
                tenengrad_variance=10557207748.7635,
                edge_rise_distance=1.5697,
                cnr=40.4423,
                leakage_ratio=10.3107,
                background_bright_spot_ratio=0.012,
                background_local_std=0.6568,
                component_count=1.0,
                solidity=0.4199,
                saturation_ratio=0.0,
                roi_entropy=7.5874,
                pai=3.5982,
                coherent_speckle_index=0.3445,
                body_area_ratio=0.2113,
            ),
            build_record(
                "typical_3",
                tenengrad_variance=8159967604.7593,
                edge_rise_distance=10.0,
                cnr=206.8208,
                leakage_ratio=65.2473,
                background_bright_spot_ratio=0.0021,
                background_local_std=0.0769,
                component_count=3.0,
                solidity=0.3297,
                saturation_ratio=0.0,
                roi_entropy=7.4669,
                pai=5.3948,
                coherent_speckle_index=0.2192,
                body_area_ratio=0.1453,
            ),
            build_record(
                "typical_4",
                tenengrad_variance=1171116468.9544,
                edge_rise_distance=7.1023,
                cnr=15.4833,
                leakage_ratio=3.5085,
                background_bright_spot_ratio=0.0143,
                background_local_std=2.3696,
                component_count=1.0,
                solidity=0.4697,
                saturation_ratio=0.025,
                roi_entropy=7.7724,
                pai=4.6266,
                coherent_speckle_index=0.1706,
                body_area_ratio=0.2619,
            ),
            build_record(
                "typical_5",
                tenengrad_variance=1206932526.5052,
                edge_rise_distance=10.0,
                cnr=12.3406,
                leakage_ratio=4.21,
                background_bright_spot_ratio=0.0193,
                background_local_std=4.5851,
                component_count=1.0,
                solidity=0.4705,
                saturation_ratio=0.0334,
                roi_entropy=7.7091,
                pai=2.9257,
                coherent_speckle_index=0.202,
                body_area_ratio=0.2892,
            ),
        ],
        DEFAULT_WEIGHTS,
    )

    order = [record["id"] for record in scored]
    assert order[:3] == ["typical_1", "typical_4", "typical_3"]
    assert order[-1] == "typical_5"
