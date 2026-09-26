# Derek's visual workbench

Run this from the repository root after installing `josh/requirements.txt`:

```bash
python3 -m streamlit run derek/visual_template.py
```

Edit `derek/visual_template.py` to try layouts, charts, and presentation ideas with
the same live World Bank data as the main dashboard. It starts with a real
paradox case and lets you preview other flagged countries. This separate app
keeps experiments out of the judge-facing pages until the team chooses a design.

Shared color and CSS settings live in `josh/theme.py`. The two judge-facing
pages are `josh/dashboard.py` and `josh/pages/1_Explore_the_map.py`.
Keep indicator fetching, country matching, and paradox calculations in
`josh/progress.py`; visual experiments can import that module without copying
or modifying its formulas.

When a visual works well, copy the relevant presentation code into the main
dashboard or map page and check both pages with real data. Keep a visible source
label and units for every metric. The two axes on the prototype chart have
different units, so label them clearly or use separate charts in the final UI.
