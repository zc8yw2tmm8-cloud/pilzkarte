"""
Farbskalen und Themen - eine Quelle fuer Karte, Bilder und Infoseite.

Zwei Skalen, weil dieselben Farben auf hellem und dunklem Grund
verschieden wirken: Dunkelrot verschwindet auf einer Nachtkarte,
Hellgelb verschwindet auf einer Tageskarte.
"""

SKALA_HELL = [
    (0.00, (120, 0, 0)),      # dunkelrot
    (0.25, (220, 30, 20)),    # rot
    (0.50, (255, 140, 0)),    # orange
    (0.65, (255, 215, 0)),    # gold
    (0.85, (80, 200, 30)),    # gruen
    (1.00, (0, 100, 0)),      # dunkelgruen
]

# Auf dunklem Grund: heller Boden, kraeftigere Mitte, kein Fast-Schwarz
SKALA_DUNKEL = [
    (0.00, (150, 40, 70)),    # weinrot, noch sichtbar
    (0.25, (225, 70, 55)),    # rot
    (0.50, (250, 155, 40)),   # orange
    (0.65, (255, 225, 90)),   # hellgelb
    (0.85, (130, 220, 70)),   # hellgruen
    (1.00, (45, 175, 75)),    # kraeftiges gruen
]

THEMEN = {
    "hell": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/"
                 "{z}/{x}/{y}{r}.png",
        "attr": "CartoDB Positron",
        "name_hell": "Karte hell",
        "kachel_deckkraft": 200,
        "grund": "#f4f4f2",
        "flaeche": "#ffffff",
        "text": "#222222",
        "text_leise": "#777777",
        "linie": "#dddddd",
        "akzent": "#2e7d32",
        "kasten": "rgba(255,255,255,.92)",
        "schutz_streng": "#c62828",
        "schutz_mild": "#1565c0",
    },
    "dunkel": {
        "tiles": "https://{s}.basemaps.cartocdn.com/dark_all/"
                 "{z}/{x}/{y}{r}.png",
        "attr": "CartoDB Dark Matter",
        "name_hell": "Karte dunkel",
        "kachel_deckkraft": 185,
        "grund": "#15181c",
        "flaeche": "#1e2228",
        "text": "#e6e6e6",
        "text_leise": "#9aa0a6",
        "linie": "#2f353d",
        "akzent": "#5fb763",
        "kasten": "rgba(24,28,33,.92)",
        "schutz_streng": "#ef5350",
        "schutz_mild": "#64b5f6",
    },
}


def skala(dunkel=False):
    return SKALA_DUNKEL if dunkel else SKALA_HELL


def thema(dunkel=False):
    return THEMEN["dunkel" if dunkel else "hell"]


def rgb(punkte, dunkel=False):
    """Score 0-100 -> (r, g, b)"""
    p = max(0, min(100, punkte)) / 100.0
    s = skala(dunkel)
    for i in range(len(s) - 1):
        p0, c0 = s[i]
        p1, c1 = s[i + 1]
        if p0 <= p <= p1:
            t = (p - p0) / (p1 - p0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
    return s[-1][1]


def hex_farbe(punkte, dunkel=False):
    r, g, b = rgb(punkte, dunkel)
    return f"#{r:02x}{g:02x}{b:02x}"
