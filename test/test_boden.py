import requests

lat, lon = 52.42, 10.79

for name, url in [
    ("Archive (ERA5)", "https://archive-api.open-meteo.com/v1/archive"),
    ("Forecast (icon_d2 + best_match)", "https://api.open-meteo.com/v1/forecast"),
]:
    parameter = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2026-07-16",
        "end_date": "2026-07-20",
        "daily": ("precipitation_sum,temperature_2m_mean,"
                  "soil_temperature_0_to_7cm_mean,soil_moisture_0_to_7cm_mean"),
        "timezone": "Europe/Berlin"
    }
    if "forecast" in url:
        parameter["models"] = "icon_d2,best_match"

    antwort = requests.get(url, params=parameter, timeout=30)
    daten = antwort.json()

    print(f"\n=== {name} ===")
    if "error" in daten:
        print("FEHLER:", daten.get("reason"))
        continue

    d = daten.get("daily", {})
    print("Verfuegbare Felder:")
    for feld in d.keys():
        if feld == "time":
            continue
        print(f"  {feld}: {d[feld]}")