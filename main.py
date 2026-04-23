import math

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from config import BAHNHOF_COORDS, HSG_COORDS, NEIGHBORHOODS
from scoring import (
    score_furnishing,
    score_location,
    score_price,
    score_student,
    score_total,
    score_transit,
    score_value,
)

st.set_page_config(page_title="HSG WG-Check", layout="wide")
st.title("HSG WG-Check")
st.caption("WG-Zimmer in St. Gallen bewerten — für HSG-Studierende")

# --- Sidebar Eingaben ---
with st.sidebar:
    st.header("Zimmer & WG")
    neighborhood = st.selectbox("Quartier", list(NEIGHBORHOODS.keys()))
    price = st.number_input("Zimmerpreis (CHF / Monat)", min_value=200, max_value=2500, value=700, step=50)
    room_size = st.number_input("Zimmergrösse (m²)", min_value=6, max_value=35, value=14, step=1)
    flatmates = st.number_input("Anzahl Mitbewohner", min_value=1, max_value=10, value=2, step=1)
    total_flat_size = st.number_input("Gesamtfläche der Wohnung (m²)", min_value=30, max_value=300, value=80, step=5)

    st.header("Ausstattung")
    own_bathroom = st.checkbox("Eigenes Bad")
    furnished = st.checkbox("Möbliert")
    floor = st.selectbox("Stockwerk", ["Erdgeschoss", "1-2", "3-4", "5+"])
    balcony = st.checkbox("Balkon / Aussenbereich")

    st.header("Extras")
    attributes = st.multiselect(
        "Zutreffendes auswählen",
        [
            "Neubau",
            "Altbau",
            "Jugendstil",
            "Kürzlich renoviert",
            "Minergie / Energieeffizient",
            "Dachgeschoss",
            "Waschmaschine in Wohnung",
            "Geschirrspüler",
            "Lift",
            "Parkett",
            "Gemeinschaftsraum / Wohnzimmer",
            "Haustiere erlaubt",
            "Gemeinsame Waschküche",
        ],
    )

# --- Scores berechnen ---
total_people = flatmates + 1
scores = {
    "price": score_price(price, total_people, neighborhood),
    "location": score_location(neighborhood),
    "value": score_value(price, room_size),
    "student": score_student(neighborhood),
    "transit": score_transit(neighborhood),
    "furnishing": score_furnishing(furnished, price, neighborhood),
}

# Komfort-Bonus (verschiebt Gesamtscore um max. ±1.0)
comfort_bonus = 0.0
if balcony:
    comfort_bonus += 0.2
if floor in ("3-4", "5+"):
    comfort_bonus += 0.15
if own_bathroom:
    comfort_bonus += 0.3

# Attribute-Bonus
ATTRIBUTE_BONUSES = {
    "Neubau": 0.15,
    "Kürzlich renoviert": 0.15,
    "Minergie / Energieeffizient": 0.1,
    "Waschmaschine in Wohnung": 0.15,
    "Geschirrspüler": 0.1,
    "Lift": 0.05,
    "Parkett": 0.05,
    "Dachgeschoss": 0.05,
    "Jugendstil": 0.05,
    "Gemeinschaftsraum / Wohnzimmer": 0.1,
    "Altbau": 0.0,
    "Haustiere erlaubt": 0.0,
    "Gemeinsame Waschküche": 0.0,
}
for attr in attributes:
    comfort_bonus += ATTRIBUTE_BONUSES.get(attr, 0.0)

total = min(10.0, max(1.0, score_total(scores) + comfort_bonus))
total = round(total, 1)

# --- Gesamtscore-Anzeige mit (i) ---
if total >= 8:
    color = "#28a745"
    verdict_word = "Ausgezeichnet"
elif total >= 5:
    color = "#ffc107"
    verdict_word = "Solide"
else:
    color = "#dc3545"
    verdict_word = "Schwach"

score_col, info_col = st.columns([6, 1])
with score_col:
    st.markdown(
        f'<div style="text-align:center;padding:0.5rem 0 0.2rem">'
        f'<span style="font-size:4.5rem;font-weight:800;color:{color}">{total}</span>'
        f'<span style="font-size:1.5rem;color:{color}"> / 10</span>'
        f'<br><span style="font-size:1.2rem;color:{color}">{verdict_word}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with info_col:
    with st.popover(":material/info:"):
        st.markdown(
            """
**So werden die Scores berechnet**

Alle Scores reichen von **1** (schlecht) bis **10** (hervorragend).

---

**Preis** (Gewicht: 25%)
Der Zimmerpreis wird mit dem geschätzten Durchschnittspreis
pro Zimmer im Quartier verglichen (Quartierdurchschnitt ÷
Anzahl Bewohner).
- Preis ≤ 70% des Durchschnitts → **10**
- Preis ≥ 160% des Durchschnitts → **1**
- Dazwischen: lineare Interpolation

**Lage** (Gewicht: 20%)
Fester Wert pro Quartier, basierend auf der Distanz und
Erreichbarkeit des HSG-Campus (Dufourstrasse 50).
Rosenberg = 9, Zentrum = 7, Winkeln = 3, usw.

**Preis-Leistung** (Gewicht: 20%)
Berechnet den Preis pro m² (Zimmerpreis ÷ Zimmergrösse).
- ≤ 20 CHF/m² → **10**
- ≥ 35 CHF/m² → **1**
- Dazwischen: lineare Interpolation

**Studifreundlichkeit** (Gewicht: 10%)
Fester Wert pro Quartier. Bewertet wie gut das Quartier für
Studierende geeignet ist: Nähe zu Studierendenwohnungen,
Einkaufsmöglichkeiten, Gastronomie, Nachtleben und Atmosphäre.
Vonwil/Zentrum = 9, St. Georgen = 8, Winkeln = 2, usw.

**ÖV-Anbindung** (Gewicht: 15%)
Fester Wert pro Quartier. Bewertet die Qualität der
ÖV-Anbindung: Anzahl Buslinien, Taktfrequenz und Nähe
zum Bahnhof. Zentrum = 10, Lachen = 8, Tablat = 7,
Bruggen = 4, usw.

**Möblierung** (Gewicht: 10%, nicht im Diagramm)
Möbliert: Startwert 8, Abzug wenn Preis weit über Durchschnitt +
200 CHF Möblierungszuschlag liegt.
Unmöbliert: Startwert 6, Abzug auf 4 wenn Preis > 120% des
Quartierdurchschnitts.

---

**Gesamtscore**
= Gewichteter Durchschnitt aller 6 Scores + Komfort-Bonus.

*Komfort-Bonus (max. ca. ±1.0):*
- Eigenes Bad: +0.3
- Balkon: +0.2
- Stockwerk 3+: +0.15
- Gemeinschaftsraum: +0.1
- Eigenschaften: z.B. Neubau +0.15, Waschmaschine +0.15,
  Geschirrspüler +0.1, Minergie +0.1, usw.

*Scores basieren aktuell auf geschätzten Durchschnittswerten
für St. Galler Quartiere.*
"""
        )

# --- Bewertungstext direkt unter Score ---
info = NEIGHBORHOODS[neighborhood]
price_per_sqm = price / room_size
avg_room_price = info["avg_rent"] / total_people
price_diff_pct = round((price / avg_room_price - 1) * 100)
shared_space = (total_flat_size - room_size * total_people) / total_people

direction = "über" if price_diff_pct > 0 else "unter"
furn_text = "möbliertes" if furnished else "unmöbliertes"
bath_text = "eigenem Bad" if own_bathroom else "geteiltem Bad"

st.markdown(
    f"Dieses **{room_size} m² {furn_text}** WG-Zimmer mit **{bath_text}** in "
    f"**{neighborhood}** ({info['vibe'].lower()}) kostet "
    f"**{abs(price_diff_pct)}% {direction}** dem geschätzten Quartierdurchschnitt "
    f"für ein Zimmer in einer {total_people}er-WG. "
    f"Mit **{price_per_sqm:.0f} CHF/m²** "
    f"{'ist das Preis-Leistungs-Verhältnis gut.' if scores['value'] >= 6 else 'ist das Preis-Leistungs-Verhältnis unterdurchschnittlich.'} "
    f"Pro Person stehen ca. **{shared_space:.0f} m²** Gemeinschaftsfläche zur Verfügung."
)

# --- Score-Darstellung in Tabs ---
labels = {
    "price": "Preis",
    "location": "Lage",
    "value": "Preis-Leistung",
    "student": "Studifreundlichkeit",
    "transit": "ÖV-Anbindung",
}

tab_bars, tab_spider, tab_map = st.tabs(["Balken", "Spinnennetz", "Karte"])

with tab_bars:
    cols = st.columns(len(labels))
    for col, (key, label) in zip(cols, labels.items()):
        s = scores[key]
        with col:
            st.metric(label, f"{s:.1f} / 10", delta=f"{s - 5:.1f}", delta_color="normal")
            st.progress(s / 10)

with tab_spider:
    categories = list(labels.values())
    values = [round(scores[k], 1) for k in labels]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(99, 110, 250, 0.15)",
        line=dict(color="rgb(99, 110, 250)", width=2.5),
        marker=dict(size=7, color="rgb(99, 110, 250)"),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickvals=[2, 4, 6, 8, 10],
                gridcolor="rgba(150, 150, 150, 0.2)",
                linecolor="rgba(150, 150, 150, 0.2)",
            ),
            angularaxis=dict(
                gridcolor="rgba(150, 150, 150, 0.2)",
                linecolor="rgba(150, 150, 150, 0.3)",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        margin=dict(l=80, r=80, t=40, b=40),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_map:
    # Generate approximate polygon for the selected neighborhood
    def make_polygon(lat: float, lon: float, radius_deg: float = 0.006, n: int = 24) -> list[list[float]]:
        """Create a circular polygon approximation around a center point."""
        return [
            [lon + radius_deg * 1.4 * math.cos(2 * math.pi * i / n),
             lat + radius_deg * math.sin(2 * math.pi * i / n)]
            for i in range(n)
        ]

    polygon = make_polygon(info["lat"], info["lon"])
    polygon_data = pd.DataFrame([{"polygon": [polygon], "name": neighborhood}])

    poi_data = pd.DataFrame([
        {"lat": HSG_COORDS["lat"], "lon": HSG_COORDS["lon"], "label": "HSG", "color": [40, 167, 69, 220]},
        {"lat": BAHNHOF_COORDS["lat"], "lon": BAHNHOF_COORDS["lon"], "label": "Bahnhof", "color": [220, 53, 69, 220]},
    ])

    center_lat = (info["lat"] + HSG_COORDS["lat"] + BAHNHOF_COORDS["lat"]) / 3
    center_lon = (info["lon"] + HSG_COORDS["lon"] + BAHNHOF_COORDS["lon"]) / 3

    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=13.5,
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                "PolygonLayer",
                data=polygon_data,
                get_polygon="polygon",
                get_fill_color=[99, 110, 250, 40],
                get_line_color=[99, 110, 250, 200],
                get_line_width=3,
                line_width_min_pixels=2,
                pickable=True,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=poi_data,
                get_position=["lon", "lat"],
                get_color="color",
                get_radius=80,
                pickable=True,
                stroked=True,
                get_line_color=[255, 255, 255],
                line_width_min_pixels=2,
            ),
            pdk.Layer(
                "TextLayer",
                data=poi_data,
                get_position=["lon", "lat"],
                get_text="label",
                get_size=14,
                get_color=[0, 0, 0, 255],
                get_pixel_offset=[0, -18],
                font_family="'Helvetica Neue', Arial, sans-serif",
                font_weight="'bold'",
            ),
        ],
        tooltip={"text": "{name}{label}"},
    ))
    st.caption("Blau: Quartier  |  Gruen: HSG  |  Rot: Bahnhof")
