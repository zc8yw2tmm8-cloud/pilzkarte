"""
Prueft, ob alle neuen Open-Meteo-Felder wirklich Werte liefern.
Immer ZUERST laufen lassen - spart lange Fehlversuche.
"""
import requests

lat, lon = 52.42, 10.79

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

url = "https://archive-api.open-meteo.com/v1/archive"
parameter = {
    "latitude": lat,
    "longitude": lon,
    "start_date": "2025-10-01",
    "end_date": "2025-10-03",
    "daily": ",".join(FELDER),
    "timezone": "Europe/Berlin",
}

antwort = requests.get(url, params=parameter, timeout=30)
daten = antwort.json()

print("=== Archive-API (ERA5) ===")
if "error" in daten:
    print("FEHLER:", daten.get("reason"))
    raise SystemExit

print("Hoehe des Punktes:", daten.get("elevation"), "m")
print()

d = daten.get("daily", {})
fehlt = []

for feld in FELDER:
    werte = d.get(feld)
    if werte is None:
        print(f"  {feld}: FELD NICHT VORHANDEN")
        fehlt.append(feld)
    elif all(w is None for w in werte):
        print(f"  {feld}: nur leere Werte")
        fehlt.append(feld)
    else:
        print(f"  {feld}: {werte}")

print()
if fehlt:
    print("Diese Felder funktionieren NICHT:")
    for f in fehlt:
        print("  -", f)
    print("\nSag mir welche - dann suche ich die richtigen Namen.")
else:
    print("Alle Felder liefern Daten. Weiter mit hintergrund.py")
