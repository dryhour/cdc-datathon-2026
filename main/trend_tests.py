"""Time-series checks for the dashboard's country evidence section."""

import warnings

import numpy as np
import streamlit as st
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss, pacf

MIN_TEST_YEARS = 6


def stationarity(series, lags):
    """Combine ADF (null: unit root) and KPSS (null: stationary); only call it when they agree."""
    adf_p = adfuller(series, regression="c", maxlag=lags, autolag=None, result_object=False)[1]
    with warnings.catch_warnings():
        # KPSS warns when its p-value falls outside the lookup table; the clipped value is still usable.
        warnings.simplefilter("ignore", InterpolationWarning)
        kpss_p = kpss(series, regression="c", nlags=lags, result_object=False)[1]
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


def yoy_percent(frame):
    """Differencing as year-over-year percent change: (this year / previous year − 1) × 100.
    A previous value of 0 has no percent change, so those years are dropped."""
    return (frame / frame.shift(1) - 1).mul(100).replace([np.inf, -np.inf], np.nan).dropna()


def yoy_correlation(yoy):
    """Correlation of the two year-over-year % change series; None with fewer than 3 years or no variation."""
    if len(yoy) < 3 or yoy.std().min() == 0:
        return None
    return yoy["access_rate"].corr(yoy["unserved"])


def correlation_label(r):
    return f"{r * 100:+.0f}%"


def co_movement(history, start, end):
    """Correlation of access rate and people without access over one period, checked with
    ADF + KPSS (stationarity), Ljung-Box and PACF (residual autocorrelation).
    Returns a dict of results, or {"skip": reason} when the tests don't apply."""
    window = history.dropna(subset=["access_rate", "unserved"])
    n = len(window)
    if n < MIN_TEST_YEARS:
        return {"skip": f"Only {n} years in {start}–{end}. Choose a period of at least {MIN_TEST_YEARS} years "
                        "to run the correlation and tests."}
    if window["access_rate"].nunique() < 3 or window["unserved"].nunique() < 3:
        return {"skip": f"At least one series barely changes in {start}–{end} (for example, 100% access every "
                        "year), so correlation and stationarity tests don't apply."}
    access, unserved = window["access_rate"], window["unserved"]
    lags = 1 if n < 12 else 2
    steps = window[["access_rate", "unserved"]].diff().dropna()
    yoy = yoy_percent(window[["access_rate", "unserved"]])
    access_state, access_adf, access_kpss = stationarity(access, lags)
    unserved_state, unserved_adf, unserved_kpss = stationarity(unserved, lags)
    # Ljung-Box on the residuals of unserved regressed on access: autocorrelated residuals flag a spurious fit.
    slope, intercept = np.polyfit(access, unserved, 1)
    residuals = unserved - (slope * access + intercept)
    lb_lags = max(1, min(3, n // 4))
    lb_p = acorr_ljungbox(residuals, lags=[lb_lags])["lb_pvalue"].iloc[0]
    resid_pacf, resid_band = lag1_pacf(residuals)
    rose = steps[steps["access_rate"] > 0]
    return {
        "n": n, "lags": lags, "lb_lags": lb_lags,
        "raw_r": access.corr(unserved),
        "diff_r": yoy_correlation(yoy),
        "access_state": access_state, "access_adf": access_adf, "access_kpss": access_kpss,
        "unserved_state": unserved_state, "unserved_adf": unserved_adf, "unserved_kpss": unserved_kpss,
        "lb_p": lb_p, "autocorrelated": lb_p < 0.05,
        "resid_pacf": resid_pacf, "resid_band": resid_band,
        "rose_years": len(rose), "grew_years": int((rose["unserved"] > 0).sum()),
        "both_rising": access.iloc[-1] > access.iloc[0] and unserved.iloc[-1] > unserved.iloc[0],
    }


def gap_grew_label(t):
    return f"{t['grew_years'] / t['rose_years'] * 100:.0f}% of years" if t["rose_years"] else "n/a"


def pacf_label(t):
    significant = abs(t["resid_pacf"]) > t["resid_band"]
    return f"{t['resid_pacf']:+.2f} ({'significant' if significant else 'not significant'})"


def render_co_movement(history, start, end, country):
    t = co_movement(history, start, end)
    if "skip" in t:
        st.info(t["skip"])
        return
    n, raw_r, diff_r = t["n"], t["raw_r"], t["diff_r"]
    access_state, unserved_state = t["access_state"], t["unserved_state"]

    trend_text = "both trend upward" if t["both_rising"] else "move over the same years"
    verdict = f"**Raw correlation: {correlation_label(raw_r)}.** Over {start}–{end}, the two series {trend_text}."
    if "Non-stationary" in (access_state, unserved_state):
        verdict += (" Because at least one series is non-stationary, part of that correlation comes from the "
                    "shared trend rather than a year-by-year link.")
    elif "Inconclusive" in (access_state, unserved_state):
        verdict += (f" With {n} years, ADF and KPSS disagree for at least one series, so stationarity is "
                    "inconclusive; a longer period gives a clearer answer.")
    else:
        verdict += " Both series are stationary, so the raw correlation isn't inflated by a shared trend."
    if t["autocorrelated"]:
        verdict += " The regression residuals are autocorrelated, so the raw correlation is likely spurious."
    else:
        verdict += " The regression residuals show no autocorrelation, so the trend relationship is fairly stable."
    if diff_r is not None:
        verdict += (f" After differencing (year-over-year % change), the correlation is {correlation_label(diff_r)}: "
                    f"years with bigger access gains had {'less' if diff_r < 0 else 'more'} gap growth.")
    st.markdown(verdict)

    t1, t2, t3 = st.columns(3)
    t1.metric("Raw correlation", correlation_label(raw_r), "levels, same years", delta_color="off")
    t2.metric("Correlation after differencing", correlation_label(diff_r) if diff_r is not None else "n/a",
              "year-over-year % change", delta_color="off")
    t3.metric("Gap grew as access rose", gap_grew_label(t),
              f"{t['grew_years']} of {t['rose_years']} years access rose", delta_color="off")
    t4, t5, t6 = st.columns(3)
    t4.metric("Access rate · stationarity", access_state, "ADF + KPSS", delta_color="off")
    t5.metric("People without access · stationarity", unserved_state, "ADF + KPSS", delta_color="off")
    t6.metric("Residual autocorrelation", "Detected" if t["autocorrelated"] else "None detected", "Ljung-Box",
              delta_color="off")
    st.caption(f"Based on {n} years ({start}–{end}); change the country or years to update."
               + (" With fewer than 15 years these tests have low statistical power." if n < 15 else ""))

    def decision(p):
        return "Reject" if p < 0.05 else "Fail to reject"

    with st.expander("Statistical details"):
        st.markdown(
            "| Test | What it checks | p-value | Result |\n"
            "|---|---|---|---|\n"
            f"| ADF · access rate | Null: unit root (non-stationary) | {t['access_adf']:.3f} | {decision(t['access_adf'])} |\n"
            f"| KPSS · access rate | Null: stationary | {t['access_kpss']:.3f} | {decision(t['access_kpss'])} |\n"
            f"| ADF · people without access | Null: unit root (non-stationary) | {t['unserved_adf']:.3f} | "
            f"{decision(t['unserved_adf'])} |\n"
            f"| KPSS · people without access | Null: stationary | {t['unserved_kpss']:.3f} | "
            f"{decision(t['unserved_kpss'])} |\n"
            f"| Ljung-Box · regression residuals | Null: no autocorrelation (lag {t['lb_lags']}) | {t['lb_p']:.3f} | "
            f"{decision(t['lb_p'])} |\n"
            f"| PACF · regression residuals | Lag-1 partial autocorrelation {t['resid_pacf']:+.2f} "
            f"(95% band ±{t['resid_band']:.2f}) | n/a | "
            f"{'Significant' if abs(t['resid_pacf']) > t['resid_band'] else 'Not significant'} |"
        )
        lags = t["lags"]
        st.caption("Significance level 0.05. A series is called stationary only when ADF rejects and KPSS does not, "
                   "and non-stationary only when KPSS rejects and ADF does not; otherwise it is inconclusive. "
                   f"ADF and KPSS use a constant and {lags} lag{'s' if lags > 1 else ''}. Correlations are Pearson r; "
                   "differencing uses year-over-year percent change. Residuals come from an OLS fit of people without access "
                   "on access rate. The unserved count is calculated from the access rate and population, so some "
                   "link between the two series is built into the data.")


def comparison_rows(t):
    """The test results as plain labels, one entry per comparison-table row."""
    if "skip" in t:
        return {"Tests": "Not enough data"}
    return {
        "Raw correlation": correlation_label(t["raw_r"]),
        "Correlation after differencing": correlation_label(t["diff_r"]) if t["diff_r"] is not None else "n/a",
        "Gap grew as access rose": gap_grew_label(t),
        "Access rate · stationarity (ADF + KPSS)": t["access_state"],
        "People without access · stationarity (ADF + KPSS)": t["unserved_state"],
        "Residual autocorrelation (Ljung-Box)": "Detected" if t["autocorrelated"] else "None detected",
        "Residual PACF, lag 1": pacf_label(t),
    }
