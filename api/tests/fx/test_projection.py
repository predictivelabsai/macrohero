import numpy as np
import pytest

from macrohero.fx.projection import ProjectionResult, fit_and_project


def test_result_dataclass_has_expected_fields() -> None:
    r = ProjectionResult(
        pair="EUR/USD",
        horizon_days=14,
        regression_window_days=252,
        r_squared=0.0,
        intercept=0.0,
        factors=[],
        projection=None,
        diagnostics={"n_observations": 0, "warnings": [], "error": None},
    )
    assert r.pair == "EUR/USD"
    assert r.factors == []


def test_fit_and_project_returns_result_with_factors_listed() -> None:
    rng = np.random.default_rng(0)
    n = 252
    f1 = rng.normal(0, 0.01, n)
    f2 = rng.normal(0, 0.01, n)
    pair_returns = 0.3 * f1 - 0.5 * f2 + rng.normal(0, 0.001, n)

    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair_returns,
        factor_names=["Brent crude", "S&P 500"],
        factor_returns=np.column_stack([f1, f2]),
        factor_transforms=["log_return", "log_return"],
        expected_factor_changes={"Brent crude": -8.0, "S&P 500": -2.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=156.40,
    )

    assert result.pair == "USD/JPY"
    assert result.horizon_days == 14
    assert len(result.factors) == 2
    names = {f.name for f in result.factors}
    assert names == {"Brent crude", "S&P 500"}
    assert result.projection is not None
    assert "n_observations" in result.diagnostics


def _make_clean_inputs(n: int = 252) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Two-factor, no-noise inputs with known beta = (0.3, -0.5)."""
    rng = np.random.default_rng(42)
    f1 = rng.normal(0, 0.01, n)
    f2 = rng.normal(0, 0.01, n)
    pair = 0.3 * f1 - 0.5 * f2
    return pair, np.column_stack([f1, f2]), ["Brent crude", "S&P 500"], ["log_return", "log_return"]


def test_known_answer_betas_recovered() -> None:
    pair, factors, names, transforms = _make_clean_inputs()
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    betas = {f.name: f.beta for f in result.factors}
    assert betas["Brent crude"] == pytest.approx(0.3, abs=1e-6)
    assert betas["S&P 500"] == pytest.approx(-0.5, abs=1e-6)
    assert result.r_squared == pytest.approx(1.0, abs=1e-6)
    assert result.intercept == pytest.approx(0.0, abs=1e-6)


def test_shock_linearity() -> None:
    pair, factors, names, transforms = _make_clean_inputs()
    base = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": -4.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    doubled = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": -8.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert base.projection is not None and doubled.projection is not None
    assert doubled.projection.point_pct == pytest.approx(2 * base.projection.point_pct, rel=1e-9)


def test_band_scales_with_sqrt_horizon() -> None:
    rng = np.random.default_rng(7)
    n = 252
    f1 = rng.normal(0, 0.01, n)
    pair = 0.2 * f1 + rng.normal(0, 0.005, n)
    common_kwargs = dict(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude"],
        factor_returns=f1.reshape(-1, 1),
        factor_transforms=["log_return"],
        expected_factor_changes={"Brent crude": 0.0},
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    r1 = fit_and_project(horizon_days=1, **common_kwargs)
    r16 = fit_and_project(horizon_days=16, **common_kwargs)
    assert r1.projection is not None and r16.projection is not None
    width_1 = r1.projection.band_95_high_pct - r1.projection.band_95_low_pct
    width_16 = r16.projection.band_95_high_pct - r16.projection.band_95_low_pct
    assert width_16 == pytest.approx(4.0 * width_1, rel=1e-9)


def test_basis_point_factor_units_passed_through() -> None:
    rng = np.random.default_rng(1)
    n = 252
    f_bp = rng.normal(0, 1.0, n)  # bp per day
    pair = 0.001 * f_bp + rng.normal(0, 0.0005, n)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["US 10Y yield"],
        factor_returns=f_bp.reshape(-1, 1),
        factor_transforms=["abs_change_bp"],
        expected_factor_changes={"US 10Y yield": 25.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert result.factors[0].unit == "bp"


def test_warns_low_r_squared_on_noise() -> None:
    rng = np.random.default_rng(11)
    n = 252
    f1 = rng.normal(0, 0.01, n)
    pair = rng.normal(0, 0.01, n)  # unrelated noise
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude"],
        factor_returns=f1.reshape(-1, 1),
        factor_transforms=["log_return"],
        expected_factor_changes={"Brent crude": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert "low_r_squared" in result.diagnostics["warnings"]


def test_warns_thin_pair_when_observations_short() -> None:
    rng = np.random.default_rng(2)
    n = 70
    f1 = rng.normal(0, 0.01, n)
    pair = 0.3 * f1
    result = fit_and_project(
        pair="USD/THIN",
        pair_returns=pair,
        factor_names=["Brent crude"],
        factor_returns=f1.reshape(-1, 1),
        factor_transforms=["log_return"],
        expected_factor_changes={"Brent crude": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=1.0,
    )
    assert "thin_pair" in result.diagnostics["warnings"]


def test_warns_singular_design_for_collinear_factors() -> None:
    rng = np.random.default_rng(3)
    n = 252
    f1 = rng.normal(0, 0.01, n)
    f2 = f1.copy()  # perfectly collinear
    pair = 0.3 * f1
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude", "WTI crude"],
        factor_returns=np.column_stack([f1, f2]),
        factor_transforms=["log_return", "log_return"],
        expected_factor_changes={"Brent crude": -5.0, "WTI crude": -5.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=1.0,
    )
    assert "singular_design" in result.diagnostics["warnings"]
    # Still returns a projection (does not raise)
    assert result.projection is not None


def test_warns_extreme_shock_beyond_three_sigma() -> None:
    rng = np.random.default_rng(4)
    n = 252
    f1 = rng.normal(0, 0.01, n)  # daily std ~1%
    pair = 0.3 * f1
    # Daily 1% std, horizon 14 → horizon std ≈ 1%·√14 ≈ 3.74%. A -50% shock is well past 3*sigma.
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude"],
        factor_returns=f1.reshape(-1, 1),
        factor_transforms=["log_return"],
        expected_factor_changes={"Brent crude": -50.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=1.0,
    )
    assert "extreme_shock" in result.diagnostics["warnings"]


# ----------------------------------------------------------------------------
# Advanced quantitative model: HAC SEs, full prediction variance, EWMA,
# per-factor inference, VIF, adjusted/OOS R^2.
# ----------------------------------------------------------------------------


def _gen_two_factor(
    n: int = 252,
    beta1: float = 0.3,
    beta2: float = -0.5,
    noise_sd: float = 0.005,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    rng = np.random.default_rng(seed)
    f1 = rng.normal(0, 0.01, n)
    f2 = rng.normal(0, 0.01, n)
    eps = rng.normal(0, noise_sd, n)
    pair = beta1 * f1 + beta2 * f2 + eps
    return (
        pair,
        np.column_stack([f1, f2]),
        ["Brent crude", "S&P 500"],
        ["log_return", "log_return"],
    )


def test_hac_standard_errors_are_finite_and_positive() -> None:
    pair, factors, names, transforms = _gen_two_factor(seed=11)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    for fc in result.factors:
        assert np.isfinite(fc.se) and fc.se > 0
        assert np.isfinite(fc.t_stat)
        assert 0.0 <= fc.p_value <= 1.0
        assert fc.ci_low < fc.beta < fc.ci_high


def test_significant_factor_has_low_p_value() -> None:
    """With strong signal and 252 obs, beta should be highly significant."""
    pair, factors, names, transforms = _gen_two_factor(seed=12, noise_sd=0.002)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    for fc in result.factors:
        assert fc.p_value < 0.01


def test_noise_factor_has_insignificant_p_value() -> None:
    """Pure noise pair vs. a single factor: p-value should not be small."""
    rng = np.random.default_rng(13)
    n = 252
    f1 = rng.normal(0, 0.01, n)
    pair = rng.normal(0, 0.01, n)  # unrelated noise
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude"],
        factor_returns=f1.reshape(-1, 1),
        factor_transforms=["log_return"],
        expected_factor_changes={"Brent crude": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert result.factors[0].p_value > 0.05


def test_vif_low_for_independent_factors() -> None:
    pair, factors, names, transforms = _gen_two_factor(seed=14)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    for fc in result.factors:
        assert fc.vif < 3.0


def test_vif_high_for_near_collinear_factors() -> None:
    """Two factors that share most of their variance should trigger
    high_collinearity well before the design becomes literally singular.
    """
    rng = np.random.default_rng(15)
    n = 252
    common = rng.normal(0, 0.01, n)
    f1 = common + rng.normal(0, 0.001, n)
    f2 = common + rng.normal(0, 0.001, n)
    pair = 0.3 * f1 - 0.5 * f2 + rng.normal(0, 0.002, n)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude", "WTI crude"],
        factor_returns=np.column_stack([f1, f2]),
        factor_transforms=["log_return", "log_return"],
        expected_factor_changes={"Brent crude": -2.0, "WTI crude": -2.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert "high_collinearity" in result.diagnostics["warnings"]
    assert result.diagnostics["max_vif"] is not None
    assert result.diagnostics["max_vif"] > 10.0


def test_full_prediction_variance_widens_band_with_large_shock() -> None:
    """Big shocks should widen the band via the parameter-variance term.
    A zero-shock band reflects only residual variance; a large-shock band
    must be strictly larger.
    """
    pair, factors, names, transforms = _gen_two_factor(seed=16, noise_sd=0.004)
    common = dict(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    r_zero = fit_and_project(
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        **common,
    )
    r_big = fit_and_project(
        expected_factor_changes={"Brent crude": -10.0, "S&P 500": -5.0},
        **common,
    )
    assert r_zero.projection is not None and r_big.projection is not None
    width_zero = r_zero.projection.band_95_high_pct - r_zero.projection.band_95_low_pct
    width_big = r_big.projection.band_95_high_pct - r_big.projection.band_95_low_pct
    assert width_big > width_zero
    # The big-shock projection should also report nonzero parameter variance.
    assert r_big.projection.parameter_variance_pct2 > 0.0
    assert r_zero.projection.parameter_variance_pct2 == pytest.approx(0.0, abs=1e-12)


def test_adjusted_r_squared_is_less_than_r_squared_when_factors_present() -> None:
    pair, factors, names, transforms = _gen_two_factor(seed=17, noise_sd=0.004)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert result.adj_r_squared < result.r_squared


def test_oos_r_squared_computed_and_close_to_in_sample_for_stable_dgp() -> None:
    pair, factors, names, transforms = _gen_two_factor(seed=18, noise_sd=0.003)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert np.isfinite(result.oos_r_squared)
    # Stable DGP, ample sample: OOS should be within ~0.2 of in-sample.
    assert abs(result.oos_r_squared - result.r_squared) < 0.2


def test_ewma_sigma_responds_to_recent_volatility_regime() -> None:
    """If the last quarter of the sample is markedly more volatile,
    sigma_ewma must exceed sigma_eps.
    """
    rng = np.random.default_rng(19)
    n = 252
    f1 = rng.normal(0, 0.01, n)
    quiet = rng.normal(0, 0.002, n - 40)
    loud = rng.normal(0, 0.02, 40)
    pair = 0.3 * f1 + np.concatenate([quiet, loud])
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=["Brent crude"],
        factor_returns=f1.reshape(-1, 1),
        factor_transforms=["log_return"],
        expected_factor_changes={"Brent crude": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    assert result.sigma_ewma > result.sigma_eps


def test_hac_lag_uses_newey_west_formula() -> None:
    pair, factors, names, transforms = _gen_two_factor(n=252, seed=20)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": 0.0, "S&P 500": 0.0},
        horizon_days=14,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    # floor(4 * (252/100)^(2/9)) = floor(4 * 1.228) = 4
    assert result.hac_lag == 4


def test_variance_decomposition_sums_to_band_half_width_squared() -> None:
    """band_half = 1.96 * sqrt(residual_var + parameter_var); verify the
    decomposition is internally consistent.
    """
    pair, factors, names, transforms = _gen_two_factor(seed=21, noise_sd=0.005)
    result = fit_and_project(
        pair="USD/JPY",
        pair_returns=pair,
        factor_names=names,
        factor_returns=factors,
        factor_transforms=transforms,
        expected_factor_changes={"Brent crude": -8.0, "S&P 500": -2.0},
        horizon_days=21,
        regression_window_days=252,
        spot_at_t0=100.0,
    )
    proj = result.projection
    assert proj is not None
    half_width_pct = (proj.band_95_high_pct - proj.band_95_low_pct) / 2.0
    total_var_pct2 = proj.residual_variance_pct2 + proj.parameter_variance_pct2
    assert half_width_pct == pytest.approx(1.96 * np.sqrt(total_var_pct2), rel=1e-9)
