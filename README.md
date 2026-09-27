# The Progress Paradox

**Carolina Data Challenge 2026 · AI for Social Good · Graduate track**
Team: Derek Perkins, Joshua Salinas

## The problem

Countries report electricity access as a percentage. That percentage can rise while the
**number of people without electricity also rises**, because the population grows faster
than new connections. A percentage-only progress report hides that growing need.

This dashboard finds where that happens, ranks the countries, and shows why.

## What it does

- Pulls live data from the **World Bank Indicators API**: electricity access
  (`EG.ELC.ACCS.ZS`) and population (`SP.POP.TOTL`), 1990–2024.
- Estimates people without electricity: `population × (1 − access rate / 100)`.
- Flags a **paradox country** when, between two chosen years, the access rate rose *and*
  the number without electricity rose.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r main/requirements.txt
.venv/bin/python -m streamlit run main/main.py
```

## Visualizations

Everything is on one page. Pick the years in the sidebar (default 2010–2024).

1. **Clickable world map.** Orange = paradox, teal = gap shrank. Click a country to explore
   it, or switch the toggle to pick a second country to compare.
2. **The evidence.** The access rate and the number without electricity, both as % change
   from the start year on the same scale, plus a bar chart of each year's % change.
3. **Do the two trends move together?** Correlation, checked with time-series tests.
4. **Compare two countries.** Side-by-side charts and a table of results.
5. **Where is the hidden gap growing?** A ranked chart that splits each paradox country's
   change into people who gained electricity vs. new people without it (population growth).

## Methods

- **Percent change** from the start year, so both series share one unit.
- **Differencing** as year-over-year % change, to remove the shared trend.
- **Correlation** (Pearson) of the raw series and of the differenced series.
- **Stationarity:** ADF and KPSS tests; a series is labeled only when both agree.
- **Autocorrelation:** Ljung-Box and PACF (lag 1) on regression residuals and yearly changes.
- **Decomposition:** each gap change split exactly into a population-growth part and an
  access-gains part (midpoint weights).

Significance level 0.05. With few years the tests have low power, so the app warns under 15 years.

## Key findings (2010–2024, the default period)

We use 2010–2024 because 15 years give the time-series tests enough data to be informative.

- **The world is improving, but the gap is concentrating.** People without electricity fell
  from 1,154M to 655M across the 215 countries with data in both years, yet **Sub-Saharan Africa's share rose from 52% to 88%**
  (596M → 579M there, while the rest of the world went from 558M to 76M).
- **16 paradox countries**, with **58.3 million more people** without electricity in total.
  **All 16 are in Sub-Saharan Africa.**
- **They did improve, just not fast enough:** the median paradox country gained 14.5
  percentage points of access (up to 22.5).
- **DR Congo** is the largest: access rose from 13.0% to 22.5%, yet **25.0M more people**
  were left without electricity. Population growth added 33.5M; access gains removed 8.5M.
- Next: Niger (+7.0M), Chad (+6.1M), Malawi (+4.7M), Mozambique (+3.2M).
- In **every** paradox country, population growth outweighed access gains.
- **A target to act on:** to hold its 2010 gap steady at its 2024 population, DR Congo
  needed **45.4% access**, about double the reported 22.5%. The app shows this for each country.
- **It isn't inevitable:** 120 countries shrank their gap by 560M people in total, led by
  India (−293M) and Bangladesh (−67M).
- For 12 of the 16, the number without electricity is **non-stationary**: a sustained
  upward trend, not year-to-year noise (ADF + KPSS).

These are estimates built from reported rates; they describe what happened and don't prove causes.

## Files

| Path | Purpose |
|---|---|
| `main/main.py` | The dashboard |
| `main/progress.py` | World Bank API fetch and paradox calculations |
| `main/trend_tests.py` | Correlation, ADF, KPSS, Ljung-Box and PACF |
| `main/export_data.py` | Saves the processed data to `main/data/` |
| `main/data/` | Processed data snapshot (country-year panel and the 2010–2024 comparison) |
| `main/theme.py` | Colors and styles |
| `main/README.md` | More detail on the method and a demo script |

## Data and citations

- World Bank, *World Development Indicators*, via the
  [Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation):
  [EG.ELC.ACCS.ZS](https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS),
  [SP.POP.TOTL](https://data.worldbank.org/indicator/SP.POP.TOTL). Licensed CC BY 4.0.
- Dickey & Fuller (1979), *JASA* 74(366) — ADF test.
- Kwiatkowski, Phillips, Schmidt & Shin (1992), *Journal of Econometrics* 54 — KPSS test.
- Ljung & Box (1978), *Biometrika* 65(2) — Ljung-Box test.
- Box & Jenkins (1970), *Time Series Analysis: Forecasting and Control* — PACF.
- Kitagawa (1955), *JASA* 50(272) — decomposing a change into components.
- Seabold & Perktold (2010), *statsmodels*, Proc. 9th Python in Science Conference.