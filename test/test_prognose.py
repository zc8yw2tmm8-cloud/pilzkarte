import requests
from datetime import date, timedelta

lat, lon = 52.42, 10.79

heute = date.today()
ende = heute + timedelta(days=6)

url = "https://api.open-meteo.com/v1/forecast"
parameter = {
    "latitude": lat,
    "longitude": lon,
    "start_date": str(heute),
    "end_date": str(ende),
    "daily": ("precipitation_sum,temperature_2m_mean,"
              "soil_temperature_0_to_7cm_mean,soil_moisture_0_to_7cm_mean"),
    "models": "icon_d2,best_match",
    "timezone": "Europe/Berlin"
}

antwort = requests.get(url, params=parameter, timeout=30)
daten = antwort.json()

if "error" in daten:
    print("FEHLER:", daten.get("reason"))
    raise SystemExit

d = daten.get("daily", {})
print("Zeitraum:", d.get("time"), "\n")

for feld, werte in d.items():
    if feld == "time":
        continue
    print(f"{feld}:")
    print(f"  {werte}")