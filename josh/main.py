import json
from urllib.request import urlopen

url = "https://api.worldbank.org/v2/country/USA/indicator/SP.POP.TOTL?format=json&date=2020:2023"

with urlopen(url) as response:
    metadata, records = json.load(response)

for record in records:
    print(record["date"], record["value"])

# testing out the api