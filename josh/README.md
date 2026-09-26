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
python3 -m pip install -r josh/requirements.txt
streamlit run josh/dashboard.py
```

The first load calls the World Bank API for country metadata, electricity access
(`EG.ELC.ACCS.ZS`), and population (`SP.POP.TOTL`). It may take several seconds.
Results are cached for 24 hours; Streamlit's **Clear cache** fetches again.

## Method

For every country and year with both indicators:

`unserved = population × (1 − access_rate / 100)`

For selected start and end years, flag a country if its access rate **increased**
and estimated unserved population **increased**. All countries use the same
endpoint years. Regional aggregates and null country-years are excluded.
The priority list ranks flagged countries by the increase in estimated people
without electricity. It does not imply that the dashboard itself connects people
to power or that population growth is the only possible explanation.
Use **Download priority list (CSV)** to take the ranked results into a briefing,
and expand the country year-by-year table to inspect the underlying observations.
Missing intermediate observations appear as gaps in the charts.

## Demo story

1. Choose a period with paradox cases and read the global count.
2. Highlight one country from the priority list.
3. Compare its two trend charts and show the source years and calculation.
4. Explain how this helps an analyst notice where a percentage-only progress
   report misses a growing number of people without access.

Sources: [World Bank electricity access](https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS),
[population](https://data.worldbank.org/indicator/SP.POP.TOTL), and
[Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation).
