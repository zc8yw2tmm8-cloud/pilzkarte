"""
Sucht eine Quelle fuer das DGM1 (1-m-Hoehenmodell).

Das LGLN stellt es unter CC BY 4.0 als Cloud-Optimized GeoTIFF bereit,
aber die Downloadadresse ist nicht dokumentiert. Dieses Skript liest
den offenen Datenkatalog des Portals aus und probiert zusaetzlich
bekannte Dienstadressen durch.
"""
import requests
import json

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

# Datenkatalog des OpenGeoData-Portals Niedersachsen
KATALOGE = [
    "https://ni-lgln-opengeodata.hub.arcgis.com/api/feed/dcat-us/1.1.json",
    "https://ni-lgln-opengeodata.hub.arcgis.com/api/feed/dcat-ap/2.1.1.json",
]

# Bekannte Dienstadressen, die es versuchen wert sind
DIENSTE = [
    ("BKG WCS DGM1", "https://sgx.geodatenzentrum.de/wcs_dgm1",
     {"service": "WCS", "version": "2.0.1", "request": "GetCapabilities"}),
    ("BKG WMS DGM1", "https://sgx.geodatenzentrum.de/wms_dgm1",
     {"service": "WMS", "version": "1.3.0", "request": "GetCapabilities"}),
    ("BKG WCS DGM5", "https://sgx.geodatenzentrum.de/wcs_dgm5",
     {"service": "WCS", "version": "2.0.1", "request": "GetCapabilities"}),
    ("LGLN DGM WMS", "https://opendata.lgln.niedersachsen.de/doorman/noauth/dgm_wms",
     {"service": "WMS", "version": "1.3.0", "request": "GetCapabilities"}),
    ("LGLN DGM WCS", "https://opendata.lgln.niedersachsen.de/doorman/noauth/dgm_wcs",
     {"service": "WCS", "version": "2.0.1", "request": "GetCapabilities"}),
]


def katalog_durchsuchen():
    print("=== Datenkatalog des Portals ===")
    for url in KATALOGE:
        print(f"\n{url.split('/')[-1]}")
        try:
            antwort = requests.get(url, headers=HEADERS, timeout=180)
            if antwort.status_code != 200:
                print(f"   HTTP {antwort.status_code}")
                continue
            daten = antwort.json()
        except Exception as e:
            print("   ", str(e)[:130])
            continue

        eintraege = daten.get("dataset") or daten.get("datasets") or []
        if not eintraege and isinstance(daten, list):
            eintraege = daten

        treffer = 0
        for e in eintraege:
            titel = str(e.get("title", ""))
            if "DGM" not in titel.upper() and "GELAENDE" not in titel.upper() \
               and "GELÄNDE" not in titel.upper():
                continue
            treffer += 1
            print(f"\n   >>> {titel}")
            for d in e.get("distribution", []):
                pfad = d.get("accessURL") or d.get("downloadURL") or ""
                art = d.get("format") or d.get("mediaType") or ""
                if pfad:
                    print(f"       [{art}] {pfad[:150]}")

        if treffer:
            return True
        print(f"   {len(eintraege)} Eintraege, kein DGM gefunden")
    return False


def dienste_pruefen():
    print("\n\n=== Bekannte Dienstadressen ===")
    gefunden = []
    for name, url, parameter in DIENSTE:
        try:
            antwort = requests.get(url, params=parameter, headers=HEADERS,
                                   timeout=60)
        except Exception as e:
            print(f"{name:16s} Verbindungsfehler: {str(e)[:70]}")
            continue

        text = antwort.text[:600]
        if antwort.status_code != 200:
            print(f"{name:16s} HTTP {antwort.status_code}")
            continue
        if "Capabilities" not in text and "capabilities" not in text.lower():
            kurz = " ".join(text.split())[:110]
            print(f"{name:16s} Antwort ohne Capabilities: {kurz}")
            continue

        print(f"{name:16s} FUNKTIONIERT")
        import re
        namen = re.findall(r"<(?:\w+:)?(?:Name|CoverageId)>([^<]+)<", antwort.text)
        for n in sorted(set(namen))[:8]:
            print(f"                  Ebene: {n}")
        gefunden.append((name, url))

    return gefunden


def main():
    print("Suche eine Quelle fuer 1-m-Hoehendaten\n")
    katalog_durchsuchen()
    gefunden = dienste_pruefen()

    print("\n" + "=" * 62)
    if gefunden:
        print("Nutzbare Dienste:")
        for name, url in gefunden:
            print(f"  {name}: {url}")
        print("\nSchick mir die Ausgabe, dann baue ich den Abruf.")
    else:
        print("Kein Dienst hat geantwortet.")
        print()
        print("Handweg, dauert fuenf Minuten:")
        print("  1. https://ni-lgln-opengeodata.hub.arcgis.com oeffnen")
        print("  2. Nach 'DGM1' suchen, Datensatz oeffnen")
        print("  3. Im Kartenfenster das Gebiet Steimker Berg waehlen")
        print("     (etwa 52.39-52.43 Nord, 10.75-10.82 Ost)")
        print("  4. Kacheln herunterladen, in einen Ordner dgm/ legen")
        print()
        print("Danach uebernimmt relief.py - das braucht keinen Dienst.")


main()
