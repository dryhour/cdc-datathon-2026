# cdc-datathon-2026
todo
# Notion
https://cdc2026.notion.site/Carolina-Data-Challenge-2026-AI-for-Social-Good-0cf43707696083e38d0081dbe7d46de6?pvs=18

# World Bank Resources
https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation


# Idea

Yes. I’d switch to The Progress Paradox. It solves a more precise data problem than the child mortality idea:
A country reports a higher percentage of people with access to a basic service—but does the number of people without it actually fall?

That can go the other way when population grows faster than access expands. The World Bank has documented this problem for electricity access in Sub-Saharan Africa. The Energy Progress Report 2025
What your tool would do: fetch access rates and population from the World Bank API, calculate people without access = population × (1 − access rate), then flag countries where the access percentage rose while the number left out also rose. Rank those places by the growing gap. A decision maker could use that to spot where an apparently improving metric is hiding a worsening human need.
I’d start with electricity because the indicators and the real-world problem are clear. Then add safely managed drinking water if its country-year coverage supports it. The World Bank provides the electricity, water, and population series through its data platform. data.worldbank.org
The demo moment is powerful: “The access rate went up. Why are more people still without access?” Your app answers it visually, identifies where it’s happening, and shows how many additional people would need to gain access just to keep the gap from growing at the recent population-growth pace. That’s a distinct, useful analysis. It helps people prioritize where to investigate and act; it doesn’t pretend a dashboard itself connects homes to power or water.






    







so how would it be with rubric













For The Progress Paradox, I’d estimate 45/50 if executed really well:
Criterion	Estimate	Why
Impact and Applicability	9/10	Helps identify places where reported progress hides a growing number of people without a basic service.
Completeness	9/10	Feasible to finish: API fetch, rate-to-people calculation, trend detection, ranking, and country detail.
Innovation and Creativity	8/10	The underlying population-growth problem is known, but turning it into an interactive alert and prioritization tool is a fresh presentation.
Visualization	10/10	Two lines moving in opposite directions—access rate up, people left out up—is immediately understandable and memorable.
Presentation	9/10	One real country example could deliver a strong reveal, followed by a clear explanation of the math and who could use it.
Total	45/50	A higher ceiling than a general health dashboard.