# The Progress Paradox — electricity access dashboard

An interactive analysis of a counterintuitive development pattern: the share of
people with electricity can rise while the number of people without electricity
also rises. The dashboard retrieves live World Bank Indicators API data and
compares identical country-year observations.

## Run locally

From the repository root:

Use Python 3.10 or newer (Python 3.12 is a good choice). Check with
`python3 --version` first. If `python3` still points to Python 3.9 on your Mac,
install a newer Python and replace `python3` below with its command, such as
`python3.12`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r main/requirements.txt
streamlit run main/main.py
```

The first load calls the World Bank API for country metadata, electricity access
(`EG.ELC.ACCS.ZS`), and population (`SP.POP.TOTL`). It may take several seconds.
Results are cached for 24 hours; Streamlit's **Clear cache** fetches again.
Choose **Map & compare** from the dashboard's sidebar to click country markers
into comparison slots A and B, or use the country dropdowns. This selector works
even when Streamlit's automatic page navigation is hidden.
The two country charts share the same axes for comparison. The map displays
only comparable countries for which World Bank country coordinates are available.

Other files in this folder:

- `map_view.py` — the map and A/B comparison, shown by **Map & compare** and by `pages/1_Explore_the_map.py`.
- `visual_template.py` — Derek's visual workbench for trying layouts and chart ideas
  (`streamlit run main/visual_template.py`).
- `progress.py` — data fetching and paradox calculations; `theme.py` — shared colors and CSS.
- `trend_tests.py` — the correlation and time-series tests (ADF, KPSS, Ljung-Box, PACF), shared by the dashboard and Map & compare.
- `api_test.py` — a minimal World Bank API request.

## Method

For every country and year with both indicators:

`unserved = population × (1 − access_rate / 100)`

For selected start and end years, flag a country if its access rate **increased**
and estimated unserved population **increased**. All countries use the same
endpoint years. Regional aggregates and null country-years are excluded.
The priority list ranks flagged countries by the increase in estimated people
without electricity. It does not imply that the dashboard itself connects people
to power or that population growth is the only possible explanation.
The ranked chart splits each flagged country's change in people without electricity into
two parts that add up exactly: people added by population growth
(`Δpopulation × average share without access`) and people removed by access gains
(`−Δaccess rate × average population`).
Use **Download priority list (CSV)** to take the ranked results into a briefing,
and expand the country year-by-year table to inspect the underlying observations.
Missing intermediate observations appear as gaps in the charts.

The two evidence charts show each series as a percent change from the start year.
Below them, the dashboard reports the Pearson correlation of the two series over the
selected years, then checks it: ADF and KPSS tests for stationarity (a series is
labeled only when both tests agree), a Ljung-Box test for autocorrelation in the
regression residuals (a sign of spurious correlation), and the correlation after
first differencing. Everything updates with the selected country and years; use at
least 6 years, and 15 or more for reliable tests. Tests use `statsmodels`.

## Demo story

1. Open the app on its default period: the strongest flagged country appears first.
2. Read the reveal, then point to the blue access-rate chart and orange unserved-count chart.
3. Show the threshold: the endpoint access rate needed to hold the earlier gap steady.
   This is a retrospective benchmark using the endpoint population, not a forecast.
4. Explore the priority ranking and export it as CSV; inspect a country's raw annual values.
5. Explain how an analyst can investigate places where a percentage-only progress
   report misses a growing number of people without access.

Sources: [World Bank electricity access](https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS),
[population](https://data.worldbank.org/indicator/SP.POP.TOTL), and
[Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation).
