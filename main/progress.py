"""World Bank electricity access analysis for the Progress Paradox dashboard."""

from concurrent.futures import ThreadPoolExecutor
import json
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "https://api.worldbank.org/v2"
ACCESS = "EG.ELC.ACCS.ZS"
POPULATION = "SP.POP.TOTL"
# Long history so per-country time-series tests have enough annual observations.
YEARS = "1990:2024"


def fetch_json(path, **params):
    query = urlencode({"format": "json", "per_page": 20000, **params})
    with urlopen(f"{BASE}/{path}?{query}", timeout=35) as response:
        data = json.load(response)
    if not isinstance(data, list) or len(data) != 2 or not isinstance(data[1], list):
        raise ValueError(f"Unexpected World Bank response for {path}: {data!r}")
    return data[1], data[0].get("lastupdated")


def load_world_bank_data(years=YEARS):
    """Fetch live country metadata and time series; return rows and update dates."""
    paths = {
        "countries": "country",
        "access": f"country/all/indicator/{ACCESS}",
        "population": f"country/all/indicator/{POPULATION}",
    }
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            name: pool.submit(fetch_json, path, date=years)
            if name != "countries" else pool.submit(fetch_json, path)
            for name, path in paths.items()
        }
        results = {name: future.result() for name, future in futures.items()}

    countries = {
        item["id"]: item
        for item in results["countries"][0]
        if item.get("region", {}).get("value") != "Aggregates"
    }

    def indexed(records):
        return {
            (item["countryiso3code"], int(item["date"])): item["value"]
            for item in records
            if item.get("value") is not None
            and item.get("countryiso3code") in countries
            and item.get("date", "").isdigit()
        }

    access = indexed(results["access"][0])
    population = indexed(results["population"][0])
    rows = []
    for (code, year), rate in access.items():
        pop = population.get((code, year))
        if pop is None or pop <= 0 or not 0 <= rate <= 100:
            continue
        rows.append({
            "code": code,
            "country": countries[code]["name"],
            "region": countries[code].get("region", {}).get("value", "").strip(),
            "latitude": _coordinate(countries[code].get("latitude")),
            "longitude": _coordinate(countries[code].get("longitude")),
            "year": year,
            "access_rate": float(rate),
            "population": int(pop),
            "unserved": pop * (1 - rate / 100),
        })
    updates = {name: result[1] for name, result in results.items()}
    return rows, updates


def compare_years(rows, start_year, end_year):
    """Compare only countries with both measures for both selected years."""
    by_key = {(r["code"], r["year"]): r for r in rows}
    codes = {r["code"] for r in rows}
    comparisons = []
    for code in codes:
        before = by_key.get((code, start_year))
        after = by_key.get((code, end_year))
        if before is None or after is None:
            continue
        delta_rate = after["access_rate"] - before["access_rate"]
        delta_unserved = after["unserved"] - before["unserved"]
        # Exact split of the gap change (midpoint weights): population_effect + access_effect == delta_unserved.
        mean_unserved_share = 1 - (before["access_rate"] + after["access_rate"]) / 200
        mean_population = (before["population"] + after["population"]) / 2
        population_effect = (after["population"] - before["population"]) * mean_unserved_share
        access_effect = -delta_rate / 100 * mean_population
        comparisons.append({
            "code": code,
            "country": after["country"],
            "latitude": after.get("latitude"),
            "longitude": after.get("longitude"),
            "start_rate": before["access_rate"],
            "end_rate": after["access_rate"],
            "start_unserved": before["unserved"],
            "end_unserved": after["unserved"],
            "start_population": before["population"],
            "end_population": after["population"],
            "population_change": after["population"] - before["population"],
            "served_change": (after["population"] - after["unserved"]) - (before["population"] - before["unserved"]),
            "delta_rate": delta_rate,
            "delta_unserved": delta_unserved,
            "population_effect": population_effect,
            "access_effect": access_effect,
            "paradox": delta_rate > 0 and delta_unserved > 0,
        })
    return sorted(comparisons, key=lambda r: r["delta_unserved"], reverse=True)


def _coordinate(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
