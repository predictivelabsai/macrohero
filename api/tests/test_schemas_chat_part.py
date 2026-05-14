from macrohero.schemas.chat import ScenarioProjectionPart


def test_scenario_projection_part_validates_minimal_payload() -> None:
    part = ScenarioProjectionPart(
        kind="scenario_projection",
        data={
            "pair": "EUR/USD",
            "horizon_days": 14,
            "regression_window_days": 252,
            "r_squared": 0.62,
            "intercept": 0.0,
            "factors": [],
            "projection": None,
            "diagnostics": {"n_observations": 0, "warnings": [], "error": None},
        },
    )
    assert part.kind == "scenario_projection"
    assert part.data["pair"] == "EUR/USD"
