# cdc-datathon-2026
todo
# Notion
https://cdc2026.notion.site/Carolina-Data-Challenge-2026-AI-for-Social-Good-0cf43707696083e38d0081dbe7d46de6?pvs=18

# World Bank Resources
https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation


# Idea

I’d build Life Expectancy Lab: Which countries achieve longer lives than countries with similar income and health spending?
A basic country dashboard would show data. This gives judges a question, a method, and a surprising result—stronger for impact, creativity, visualization, and presentation.
Part	What we build
World view	Scatterplot: GDP per person vs. life expectancy. Highlight countries above and below their peers.
Country explorer	Pick a country and show its five closest peers by income and health spending.
“Life expectancy gap”	Compare its life expectancy with the peer median, in years.
History	Show whether that gap has widened or narrowed over time.
Explanation	Show the actual values, year, source, and missing-data notes behind every comparison.


The World Bank has indicators for life expectancy, GDP per capita adjusted for purchasing power, and health expenditure per person. We’d retrieve them through the API in the app, satisfying the track requirement. Data
First build: fetch those three indicators, join records by country and year, exclude records missing a required value, then make the scatterplot. After that, add peer matching and the country story. We should call the gap a comparison, not claim health spending caused it.
My vote is this over a general “compare any two countries” app. It has a much clearer 2-minute demo: pick a country → reveal its peers → show the gap → show how it changed.