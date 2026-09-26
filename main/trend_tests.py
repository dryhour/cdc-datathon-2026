"""Time-series checks shared by the dashboard and the map comparison."""

import warnings

import numpy as np
import streamlit as st
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss, pacf

MIN_TEST_YEARS = 6


def stationarity(series, lags):
    """Combine ADF (null: unit root) and KPSS (null: stationary); only call it when they agree."""
    adf_p = adfuller(series, regression="c", maxlag=lags, autolag=None)[1]
    with warnings.catch_warnings():
        # KPSS warns when its p-value falls outside the lookup table; the clipped value is still usable.
        warnings.simplefilter("ignore", InterpolationWarning)
        kpss_p = kpss(series, regression="c", nlags=lags)[1]
    if adf_p < 0.05 and kpss_p >= 0.05:
        label = "Stationary"
    elif adf_p >= 0.05 and kpss_p < 0.05:
        label = "Non-stationary"
    else:
        label = "Inconclusive"
    return label, adf_p, kpss_p


def lag1_pacf(series):
    """Lag-1 partial autocorrelation and its 95% band (±1.96/√n)."""
    return pacf(series, nlags=1, method="ywm")[1], 1.96 / np.sqrt(len(series))


def correlation_label(r):
    return f"{r * 100:+.0f}%"


def render_co_movement(history, start, end, country, compact=False):
    """Correlation of access rate and people without access over one period, checked with
    ADF + KPSS (stationarity), Ljung-Box and PACF (residual autocorrelation)."""
    window = history.dropna(subset=["access_rate", "unserved"])
    n = len(window)
    if n < MIN_TEST_YEARS:
        st.info(f"Only {n} years in {start}–{end}. Choose a period of at least {MIN_TEST_YEARS} years "
                "to run the correlation and tests.")
    elif window["access_rate"].nunique() < 3 or window["unserved"].nunique() < 3:
        st.info(f"At least one series barely changes in {start}–{end} (for example, 100% access every year), "
                "so correlation and stationarity tests don't apply.")
    else:
        access, unserved = window["access_rate"], window["unserved"]
        lags = 1 if n < 12 else 2
        raw_r = access.corr(unserved)
        steps = window[["access_rate", "unserved"]].diff().dropna()
        diff_r = steps["access_rate"].corr(steps["unserved"]) if steps.std().min() > 0 else None
        access_state, access_adf, access_kpss = stationarity(access, lags)
        unserved_state, unserved_adf, unserved_kpss = stationarity(unserved, lags)
        # Ljung-Box on the residuals of unserved regressed on access: autocorrelated residuals flag a spurious fit.
        slope, intercept = np.polyfit(access, unserved, 1)
        residuals = unserved - (slope * access + intercept)
        lb_lags = max(1, min(3, n // 4))
        lb_p = acorr_ljungbox(residuals, lags=[lb_lags])["lb_pvalue"].iloc[0]
        autocorrelated = lb_p < 0.05
        resid_pacf, resid_band = lag1_pacf(residuals)
        rose = steps[steps["access_rate"] > 0]
        grew = int((rose["unserved"] > 0).sum())

        both_rising = access.iloc[-1] > access.iloc[0] and unserved.iloc[-1] > unserved.iloc[0]
        trend_text = "both trend upward" if both_rising else "move over the same years"
        verdict = f"**Raw correlation: {correlation_label(raw_r)}.** Over {start}–{end}, the two series {trend_text}."
        if "Non-stationary" in (access_state, unserved_state):
            verdict += (" Because at least one series is non-stationary, part of that correlation comes from the "
                        "shared trend rather than a year-by-year link.")
        elif "Inconclusive" in (access_state, unserved_state):
            verdict += (f" With {n} years, ADF and KPSS disagree for at least one series, so stationarity is "
                        "inconclusive; a longer period gives a clearer answer.")
        else:
            verdict += " Both series are stationary, so the raw correlation isn't inflated by a shared trend."
        if autocorrelated:
            verdict += " The regression residuals are autocorrelated, so the raw correlation is likely spurious."
        else:
            verdict += " The regression residuals show no autocorrelation, so the trend relationship is fairly stable."
        if diff_r is not None:
            verdict += (f" After differencing, the correlation is {correlation_label(diff_r)}: years with bigger access "
                        f"gains had {'less' if diff_r < 0 else 'more'} gap growth.")
        st.markdown(verdict)

        per_row = 2 if compact else 3
        cells = [cell for _ in range(0, 6, per_row) for cell in st.columns(per_row)]
        t1, t2, t3, t4, t5, t6 = cells
        t1.metric("Raw correlation", correlation_label(raw_r), "levels, same years", delta_color="off")
        t2.metric("Correlation after differencing", correlation_label(diff_r) if diff_r is not None else "n/a",
                  "year-to-year changes", delta_color="off")
        t3.metric("Gap grew as access rose", f"{grew / len(rose) * 100:.0f}% of years" if len(rose) else "n/a",
                  f"{grew} of {len(rose)} years access rose", delta_color="off")
        t4.metric("Access rate · stationarity", access_state, "ADF + KPSS", delta_color="off")
        t5.metric("People without access · stationarity", unserved_state, "ADF + KPSS", delta_color="off")
        t6.metric("Residual autocorrelation", "Detected" if autocorrelated else "None detected", "Ljung-Box",
                  delta_color="off")
        st.caption(f"Based on {n} years ({start}–{end}); change the country or years to update."
                   + (" With fewer than 15 years these tests have low statistical power." if n < 15 else ""))

        with st.expander("Statistical details"):
            st.markdown(
                "| Test | What it checks | p-value | Result |\n"
                "|---|---|---|---|\n"
                f"| ADF · access rate | Null: unit root (non-stationary) | {access_adf:.3f} | "
                f"{'Reject' if access_adf < 0.05 else 'Fail to reject'} |\n"
                f"| KPSS · access rate | Null: stationary | {access_kpss:.3f} | "
                f"{'Reject' if access_kpss < 0.05 else 'Fail to reject'} |\n"
                f"| ADF · people without access | Null: unit root (non-stationary) | {unserved_adf:.3f} | "
                f"{'Reject' if unserved_adf < 0.05 else 'Fail to reject'} |\n"
                f"| KPSS · people without access | Null: stationary | {unserved_kpss:.3f} | "
                f"{'Reject' if unserved_kpss < 0.05 else 'Fail to reject'} |\n"
                f"| Ljung-Box · regression residuals | Null: no autocorrelation (lag {lb_lags}) | {lb_p:.3f} | "
                f"{'Reject' if autocorrelated else 'Fail to reject'} |\n"
                f"| PACF · regression residuals | Lag-1 partial autocorrelation {resid_pacf:+.2f} "
                f"(95% band ±{resid_band:.2f}) | n/a | "
                f"{'Significant' if abs(resid_pacf) > resid_band else 'Not significant'} |"
            )
            st.caption("Significance level 0.05. A series is called stationary only when ADF rejects and KPSS does not, "
                       "and non-stationary only when KPSS rejects and ADF does not; otherwise it is inconclusive. "
                       f"ADF and KPSS use a constant and {lags} lag{'s' if lags > 1 else ''}. Correlations are Pearson r; "
                       "differencing uses first differences. Residuals come from an OLS fit of people without access "
                       "on access rate. The unserved count is calculated from the access rate and population, so some "
                       "link between the two series is built into the data.")
