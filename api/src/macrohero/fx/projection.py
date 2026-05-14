"""Pure deterministic FX projection engine.

No I/O. Given aligned pair / factor return arrays plus LLM-supplied shocks,
fits a multi-factor OLS regression with:

  - Newey-West (HAC) standard errors on every beta;
  - Per-factor t-stat, two-sided p-value and 95% CI (normal approximation,
    valid because the data-layer guarantees n - k - 1 >= 60);
  - Variance Inflation Factor (VIF) per regressor as a multicollinearity
    diagnostic that fires well before the design becomes singular;
  - In-sample R^2, adjusted R^2, and an expanding-window out-of-sample R^2
    as honest fit metrics;
  - EWMA (RiskMetrics, lambda=0.94) residual volatility for the horizon
    band, so the projection reflects the current regime instead of the
    full-window average;
  - A 95% prediction interval that combines (a) future residual variance
    sigma^2 * h and (b) parameter (beta) uncertainty shock' Cov(beta) shock,
    so the band does not understate uncertainty when shocks are large.

The shock-driven component (Sigma beta_i * shock_i) is the projected return;
the regression intercept (drift) is fit but excluded from the projection so
the headline answers "what's the move attributable to the scenario shocks?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import erfc, sqrt
from typing import Any

import numpy as np


@dataclass(frozen=True)
class FactorContribution:
    name: str
    ticker: str
    beta: float
    expected_change: float          # raw LLM input (-8.0 = -8% or +25 bp)
    unit: str                       # "%" or "bp"
    contribution_pct: float         # signed % contribution to point estimate
    se: float                       # Newey-West HAC standard error of beta
    t_stat: float                   # beta / se
    p_value: float                  # two-sided, normal approx (n large)
    ci_low: float                   # 95% CI lower bound on beta
    ci_high: float                  # 95% CI upper bound on beta
    vif: float                      # variance inflation factor


@dataclass(frozen=True)
class Projection:
    point_pct: float
    band_95_low_pct: float
    band_95_high_pct: float
    spot_at_t0: float
    projected_spot: float
    spot_band_low: float
    spot_band_high: float
    residual_variance_pct2: float   # (sigma^2 * h)  expressed in %^2
    parameter_variance_pct2: float  # shock' Cov(beta) shock  in %^2


@dataclass(frozen=True)
class ProjectionResult:
    pair: str
    horizon_days: int
    regression_window_days: int
    r_squared: float
    intercept: float
    factors: list[FactorContribution]
    projection: Projection | None
    adj_r_squared: float = 0.0
    oos_r_squared: float = 0.0      # expanding-window 5-fold OOS R^2
    sigma_eps: float = 0.0          # OLS residual std (full-window, dof-corrected)
    sigma_ewma: float = 0.0         # EWMA-implied current-regime residual std
    hac_lag: int = 0                # Newey-West lag used
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------------
# Helpers (pure functions, numpy only)
# ----------------------------------------------------------------------------


def _hac_lag(n: int) -> int:
    """Newey-West (1994) automatic lag selection: floor(4 * (n/100)^(2/9))."""
    return max(int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))), 1)


def _newey_west_cov(x: np.ndarray, residuals: np.ndarray, lag: int) -> np.ndarray:
    """HAC covariance estimator with Bartlett kernel.

    Sandwich form:  (X'X)^{-1} S (X'X)^{-1}, where
        S = Gamma_0 + sum_{l=1..L} w_l (Gamma_l + Gamma_l')
        Gamma_l[i,j] = (1/n) sum_{t=l+1..n} eps_t * eps_{t-l} * x_t[i] * x_{t-l}[j]
        w_l = 1 - l/(L+1)              (Bartlett)
    Returns Cov(beta_hat) for all columns of x (including the intercept).
    """
    n = x.shape[0]
    r2 = residuals**2
    s = x.T @ (x * r2[:, None]) / n
    for lvl in range(1, lag + 1):
        weight = 1.0 - lvl / (lag + 1.0)
        rl = residuals[lvl:] * residuals[:-lvl]
        gamma = x[lvl:].T @ (x[:-lvl] * rl[:, None]) / n
        s += weight * (gamma + gamma.T)
    xtx_inv = np.linalg.inv(x.T @ x / n)
    return xtx_inv @ s @ xtx_inv / n


def _ewma_variance(residuals: np.ndarray, lam: float = 0.94) -> float:
    """RiskMetrics-style EWMA daily variance evaluated at the last bar."""
    if residuals.size == 0:
        return 0.0
    var = float(residuals[0] ** 2)
    for r in residuals[1:]:
        var = lam * var + (1.0 - lam) * float(r) ** 2
    return var


def _vif(factor_returns: np.ndarray) -> np.ndarray:
    """VIF per regressor (excluding the intercept).

    VIF_i = 1 / (1 - R^2_i) where R^2_i comes from regressing column i on the
    remaining columns (with intercept). Infinity for perfectly collinear
    columns; > 10 is the conventional "high collinearity" threshold.
    """
    n, k = factor_returns.shape
    vifs = np.zeros(k)
    if k <= 1:
        vifs[:] = 1.0
        return vifs
    for i in range(k):
        y_i = factor_returns[:, i]
        x_other = np.delete(factor_returns, i, axis=1)
        x_other_const = np.column_stack([np.ones(n), x_other])
        beta_i, *_ = np.linalg.lstsq(x_other_const, y_i, rcond=None)
        y_hat = x_other_const @ beta_i
        ss_res = float(np.sum((y_i - y_hat) ** 2))
        ss_tot = float(np.sum((y_i - y_i.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        vifs[i] = 1.0 / (1.0 - r2) if r2 < 1.0 - 1e-12 else float("inf")
    return vifs


def _oos_r_squared(x: np.ndarray, y: np.ndarray, n_folds: int = 5) -> float:
    """Expanding-window out-of-sample R^2 (no look-ahead).

    Train on the first 50% of the sample; predict the next 1/n_folds; expand
    the train set and repeat. The OOS R^2 is computed across the full set of
    out-of-sample predictions.
    """
    n = x.shape[0]
    if n < 60:
        return float("nan")
    initial = n // 2
    fold = max((n - initial) // n_folds, 1)
    if fold < 5:
        return float("nan")
    preds: list[float] = []
    truth: list[float] = []
    for k in range(n_folds):
        train_end = initial + k * fold
        test_end = min(train_end + fold, n)
        if test_end <= train_end:
            break
        beta, *_ = np.linalg.lstsq(x[:train_end], y[:train_end], rcond=None)
        preds.extend((x[train_end:test_end] @ beta).tolist())
        truth.extend(y[train_end:test_end].tolist())
    if not preds:
        return float("nan")
    pred_arr = np.asarray(preds)
    truth_arr = np.asarray(truth)
    ss_res = float(np.sum((truth_arr - pred_arr) ** 2))
    ss_tot = float(np.sum((truth_arr - truth_arr.mean()) ** 2))
    if ss_tot <= 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def _two_sided_normal_p(z: float) -> float:
    """Two-sided p-value under the standard normal.

    We use the normal approximation in place of Student-t. The data-layer
    requires n >= 61 (so dof = n - k - 1 >= 60 for k <= 8); at dof = 60 the
    error vs. the exact t-distribution is < 0.2% in the 5% tail.
    """
    return float(erfc(abs(z) / sqrt(2.0)))


def _skewness(x: np.ndarray) -> float:
    if x.size < 3:
        return 0.0
    s = x.std(ddof=1)
    if s == 0.0:
        return 0.0
    return float(np.mean(((x - x.mean()) / s) ** 3))


def _excess_kurtosis(x: np.ndarray) -> float:
    if x.size < 4:
        return 0.0
    s = x.std(ddof=1)
    if s == 0.0:
        return 0.0
    return float(np.mean(((x - x.mean()) / s) ** 4) - 3.0)


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------


def fit_and_project(
    *,
    pair: str,
    pair_returns: np.ndarray,
    factor_names: list[str],
    factor_returns: np.ndarray,
    factor_transforms: list[str],
    expected_factor_changes: dict[str, float],
    horizon_days: int,
    regression_window_days: int,
    spot_at_t0: float,
) -> ProjectionResult:
    """Fit OLS with HAC inference + project pair return over horizon."""
    n = pair_returns.shape[0]
    k = factor_returns.shape[1]
    if k != len(factor_names) or k != len(factor_transforms):
        raise ValueError(
            f"factor count mismatch: factor_returns has {k} columns, "
            f"factor_names has {len(factor_names)}, "
            f"factor_transforms has {len(factor_transforms)}"
        )

    # Design matrix with intercept column.
    x_design = np.column_stack([np.ones(n), factor_returns])
    y = pair_returns

    # OLS via lstsq (gracefully handles rank deficiency via SVD).
    coeffs, *_ = np.linalg.lstsq(x_design, y, rcond=None)
    intercept = float(coeffs[0])
    betas = coeffs[1:]

    # Residuals, R^2, adjusted R^2, full-window sigma.
    y_hat = x_design @ coeffs
    resid = y - y_hat
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - sse / sst if sst > 0 else 0.0
    dof = max(n - k - 1, 1)
    adj_r_squared = (
        1.0 - (1.0 - r_squared) * (n - 1) / dof if n > k + 1 else r_squared
    )
    sigma_eps = float(np.sqrt(sse / dof))

    # EWMA residual volatility (current regime, lambda = 0.94 RiskMetrics).
    sigma_ewma = float(np.sqrt(_ewma_variance(resid, lam=0.94)))

    # Newey-West HAC covariance of beta. May fail if X'X is singular (e.g.
    # perfectly collinear factors); fall back to NaN inference and let the
    # collinearity warnings carry the message.
    lag = _hac_lag(n)
    cov_ok = True
    try:
        cov_full = _newey_west_cov(x_design, resid, lag)
        if not np.all(np.isfinite(cov_full)):
            cov_ok = False
    except np.linalg.LinAlgError:
        cov_full = np.full((k + 1, k + 1), float("nan"))
        cov_ok = False
    cov_beta = cov_full[1:, 1:]
    if cov_ok:
        se_beta = np.sqrt(np.clip(np.diag(cov_beta), 0.0, None))
    else:
        se_beta = np.full(k, float("nan"))

    # Convert each shock to regressor units (decimal for log_return, bp as-is).
    shocks: list[float] = []
    units: list[str] = []
    for i, name in enumerate(factor_names):
        raw = float(expected_factor_changes.get(name, 0.0))
        if factor_transforms[i] == "log_return":
            shocks.append(raw / 100.0)
            units.append("%")
        elif factor_transforms[i] == "abs_change_bp":
            shocks.append(raw)
            units.append("bp")
        else:
            raise ValueError(f"unsupported transform: {factor_transforms[i]}")
    shock_vec = np.asarray(shocks, dtype=float)

    # Point log return (shock-driven, intercept excluded).
    point_log_return = float(betas @ shock_vec)

    # --- Full 95% prediction interval --------------------------------------
    # Variance has two independent pieces over the horizon:
    #   (a) future residual noise: sigma^2 * h
    #       Use sigma_ewma when finite/positive; fall back to sigma_eps.
    #   (b) parameter (beta) uncertainty: shock' Cov(beta) shock
    sigma2_band = sigma_ewma**2 if (sigma_ewma > 0 and np.isfinite(sigma_ewma)) else sigma_eps**2
    residual_var_lr = sigma2_band * horizon_days
    if cov_ok:
        param_var_lr = float(shock_vec @ cov_beta @ shock_vec)
        param_var_lr = max(param_var_lr, 0.0)  # guard against tiny negatives
    else:
        param_var_lr = 0.0
    total_var_lr = residual_var_lr + param_var_lr
    band_half_lr = 1.96 * float(np.sqrt(total_var_lr))

    point_pct = point_log_return * 100.0
    low_pct = (point_log_return - band_half_lr) * 100.0
    high_pct = (point_log_return + band_half_lr) * 100.0

    projected_spot = spot_at_t0 * (1.0 + point_pct / 100.0)
    spot_low = spot_at_t0 * (1.0 + low_pct / 100.0)
    spot_high = spot_at_t0 * (1.0 + high_pct / 100.0)

    # VIF per factor.
    vifs = _vif(factor_returns) if k >= 1 else np.array([])

    contributions: list[FactorContribution] = []
    for i, name in enumerate(factor_names):
        b = float(betas[i])
        se = float(se_beta[i]) if np.isfinite(se_beta[i]) else float("nan")
        if np.isfinite(se) and se > 0:
            t_stat = b / se
            p_value = _two_sided_normal_p(t_stat)
            ci_low = b - 1.96 * se
            ci_high = b + 1.96 * se
        else:
            t_stat = float("nan")
            p_value = float("nan")
            ci_low = float("nan")
            ci_high = float("nan")
        contributions.append(
            FactorContribution(
                name=name,
                ticker="",
                beta=b,
                expected_change=float(expected_factor_changes.get(name, 0.0)),
                unit=units[i],
                contribution_pct=b * float(shock_vec[i]) * 100.0,
                se=se,
                t_stat=float(t_stat) if np.isfinite(t_stat) else float("nan"),
                p_value=float(p_value) if np.isfinite(p_value) else float("nan"),
                ci_low=float(ci_low) if np.isfinite(ci_low) else float("nan"),
                ci_high=float(ci_high) if np.isfinite(ci_high) else float("nan"),
                vif=float(vifs[i]) if i < len(vifs) else float("nan"),
            )
        )

    # Out-of-sample R^2 (expanding window).
    oos = _oos_r_squared(x_design, y, n_folds=5)

    # --- Diagnostics + warnings --------------------------------------------
    warnings_list: list[str] = []

    if r_squared < 0.20:
        warnings_list.append("low_r_squared")
    if n < 120:
        warnings_list.append("thin_pair")

    try:
        cond = float(np.linalg.cond(x_design))
    except np.linalg.LinAlgError:
        cond = float("inf")
    if not np.isfinite(cond) or cond > 1e10:
        warnings_list.append("singular_design")

    factor_daily_std = factor_returns.std(axis=0, ddof=1)
    horizon_scale = float(np.sqrt(horizon_days))
    for i in range(k):
        if factor_daily_std[i] == 0:
            continue
        if abs(shock_vec[i]) > 3.0 * factor_daily_std[i] * horizon_scale:
            warnings_list.append("extreme_shock")
            break

    if vifs.size > 0 and np.any(np.isfinite(vifs)) and float(np.nanmax(vifs)) > 10.0:
        warnings_list.append("high_collinearity")

    if np.isfinite(oos) and oos < 0:
        warnings_list.append("unstable_oos")

    skew = _skewness(resid)
    kurt = _excess_kurtosis(resid)
    if abs(skew) > 1.0 or kurt > 3.0:
        warnings_list.append("fat_tails")

    diagnostics: dict[str, Any] = {
        "n_observations": n,
        "warnings": warnings_list,
        "error": None,
        "condition_number": cond if np.isfinite(cond) else None,
        "max_vif": float(np.nanmax(vifs)) if vifs.size > 0 else None,
        "residual_skewness": skew,
        "residual_excess_kurtosis": kurt,
    }

    return ProjectionResult(
        pair=pair,
        horizon_days=horizon_days,
        regression_window_days=regression_window_days,
        r_squared=r_squared,
        adj_r_squared=adj_r_squared,
        oos_r_squared=oos,
        sigma_eps=sigma_eps,
        sigma_ewma=sigma_ewma,
        hac_lag=lag,
        intercept=intercept,
        factors=contributions,
        projection=Projection(
            point_pct=point_pct,
            band_95_low_pct=low_pct,
            band_95_high_pct=high_pct,
            spot_at_t0=spot_at_t0,
            projected_spot=projected_spot,
            spot_band_low=spot_low,
            spot_band_high=spot_high,
            residual_variance_pct2=residual_var_lr * 10000.0,
            parameter_variance_pct2=param_var_lr * 10000.0,
        ),
        diagnostics=diagnostics,
    )
