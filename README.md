# cdc-datathon-2026
todo
# Notion
https://cdc2026.notion.site/Carolina-Data-Challenge-2026-AI-for-Social-Good-0cf43707696083e38d0081dbe7d46de6?pvs=18

# World Bank Resources
https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation


# Idea

I’d pivot to Child Survival Gap. This has a stronger shot at the rubric’s impact and innovation points.
Question: Which countries have higher under-five mortality than similarly resourced countries, how large is the gap, and what measurable conditions distinguish the better-performing peers?

Hypothesis: Income and health spending don’t fully explain child survival. Some countries will have substantially lower under-five mortality than peers with similar resources.
The app would fetch World Bank API data and:
1. Match countries with similar GDP per person and health spending per person.
2. Compare their under-five mortality rates to find unusually large gaps.
3. Show the gap on a map and a peer comparison chart.
4. Let judges click a country to see its trend alongside peers, plus context such as immunization, drinking water, and sanitation.
5. Generate a plain-language “investigate this gap” brief with the numbers and source years—not an unsupported claim that one factor caused it.
The World Bank has the indicators needed for under-five mortality, immunization, drinking water, and sanitation. Data
Why I like it more: the finding is specific and human: “Countries with similar resources have different child survival outcomes.” You’re using data to identify and prioritize a real gap, then giving people a way to investigate it. That’s a much stronger presentation than “here are global health charts.”
Could it score 50/50? Potentially, yes—if the matching is defensible, the API pipeline works reliably, the visualizations are excellent, and you find one compelling real example. No concept guarantees 50. But this is the one I’d choose if we’re trying to win.