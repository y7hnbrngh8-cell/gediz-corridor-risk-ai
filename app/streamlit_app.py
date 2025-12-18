from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import networkx as nx

from src.graph.corridor_graph import build_corridor_graph, subgraph_for_species, bottleneck_scores
from src.risk.risk_engine import DroughtSignals, compute_risk
from src.io.drought_loader import load_drought_table, pick_signals

st.set_page_config(page_title="Gediz Koridor Risk Zekâsı", layout="wide")
st.title("Gediz Koridor Risk Zekâsı")
st.caption("Koridor grafı + açıklanabilir risk motoru + 1–3 ay erken uyarı + eylem önerileri (MVP)")

st.sidebar.header("Kontroller")
species_label = st.sidebar.selectbox("Tür", ["Flamingo", "Pelican"], index=0)
node = st.sidebar.selectbox("Düğüm", ["Gediz", "Kerkini", "Tuz", "Camargue", "Tuna", "EastMed"], index=0)
month = st.sidebar.slider("Ay (1-12)", 1, 12, 6, 1)

st.sidebar.subheader("Kuraklık Sinyalleri (CSV’den)")
region = st.sidebar.selectbox("Bölge", ["Ege"], index=0)

df_drought = load_drought_table()
signals = pick_signals(df_drought, month=month, region=region)

st.sidebar.subheader("Kuraklık ve İklim Durumu (Özet)")

def drought_level_spi(x):
    if x <= -2.0:
        return "Şiddetli"
    if x <= -1.5:
        return "Orta"
    if x <= -1.0:
        return "Hafif"
    return "Normal"

col1, col2 = st.sidebar.columns(2)

with col1:
    st.sidebar.metric(
        "SPI-12",
        f"{signals.spi12:.1f}",
        drought_level_spi(signals.spi12)
    )

with col2:
    st.sidebar.metric(
        "SPI-24",
        f"{signals.spi24:.1f}",
        drought_level_spi(signals.spi24)
    )

st.sidebar.markdown("**CDI Uyarı Seviyesi**")
if signals.cdi == "alert":
    st.sidebar.error("Alert – Acil kuraklık koşulları")
elif signals.cdi == "warning":
    st.sidebar.warning("Warning – Kuraklık riski artıyor")
elif signals.cdi == "watch":
    st.sidebar.info("Watch – İzleme önerilir")
else:
    st.sidebar.success("Normal")

st.sidebar.subheader("Maruziyet (Düğüm Su Stresi)")
base_water_stress = st.sidebar.slider(
    "Gediz düğümü su stresi (0=düşük, 1=çok yüksek)",
    0.0,
    1.0,
    0.9,
    0.05
)

st.sidebar.subheader("Ağırlıklar (Risk Motoru)")
w_h = st.sidebar.slider("Hazard ağırlığı", 0.0, 1.0, 0.45, 0.05)
w_e = st.sidebar.slider("Exposure ağırlığı", 0.0, 1.0, 0.35, 0.05)
w_s = st.sidebar.slider("Sensitivity ağırlığı", 0.0, 1.0, 0.20, 0.05)

s = w_h + w_e + w_s
weights = {"hazard": 0.45, "exposure": 0.35, "sensitivity": 0.20} if s == 0 else {
    "hazard": w_h / s, "exposure": w_e / s, "sensitivity": w_s / s
}

G = build_corridor_graph()
Gsp = subgraph_for_species(G, species_label)
btw = bottleneck_scores(Gsp)

result = compute_risk(
    G_species=Gsp,
    species=species_label,
    node=node,
    month=month,
    signals=signals,
    base_water_stress=base_water_stress,
    weights=weights,
)

left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("Koridor Haritası (Graph)")
    pos = nx.spring_layout(Gsp, seed=7)

    edge_x, edge_y = [], []
    for u, v in Gsp.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=2), hoverinfo="none")

    node_x, node_y, texts, sizes = [], [], [], []
    for n in Gsp.nodes():
        x, y = pos[n]
        node_x.append(x); node_y.append(y)
        b = btw.get(n, 0.0)
        texts.append(f"{n}<br>Darboğaz(betweenness): {b:.3f}")
        sizes.append(18 + 55 * b)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=[n for n in Gsp.nodes()],
        textposition="top center",
        hovertext=texts, hoverinfo="text",
        marker=dict(size=sizes, line=dict(width=1)),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=520)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Not: Düğüm boyutu, tür bazlı koridor grafında darboğaz (betweenness) etkisini temsil eder (MVP).")
        # --- Mini Lokasyon Haritası (Gediz Deltası) ---
    st.markdown("#### Gediz Deltası (Konum)")

    # Basit koordinatlar (istersen sonra genişletiriz)
    places = {
        "Gediz Delta": {"lat": 38.52, "lon": 26.95},
        # Diğer düğümler (yaklaşık, opsiyonel):
        "Tuz": {"lat": 38.73, "lon": 33.33},
        "Kerkini": {"lat": 41.21, "lon": 23.10},
        "Camargue": {"lat": 43.52, "lon": 4.42},
        "Tuna": {"lat": 45.20, "lon": 29.60},
        "EastMed": {"lat": 34.90, "lon": 35.20},
    }

    # Seçili node için gösterilecek isim
    node_key = "Gediz Delta" if node == "Gediz" else node
    if node_key not in places:
        node_key = "Gediz Delta"

    lat = places[node_key]["lat"]
    lon = places[node_key]["lon"]

    mini_map = go.Figure(
        go.Scattergeo(
            lon=[lon],
            lat=[lat],
            text=[node_key],
            mode="markers+text",
            marker=dict(size=12),
            textposition="top center",
        )
    )

    mini_map.update_geos(
        showcountries=True,
        showland=True,
        showlakes=True,
        projection_type="natural earth",
        lataxis_range=[30, 50],
        lonaxis_range=[15, 45],
    )
    mini_map.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
    )

    st.plotly_chart(mini_map, use_container_width=True)
    st.caption("Bu harita, seçilen düğümün yaklaşık konumunu gösterir (MVP).")

st.divider()
st.subheader("Gediz Deltası – Mekânsal Risk Durumu")

def _lvl(x: float) -> str:
    return "Yüksek" if x >= 0.70 else "Orta" if x >= 0.40 else "Düşük"

haz = result.components["hazard"]
exp = result.components["exposure"]
sen = result.components["sensitivity"]

c1, c2 = st.columns(2)

with c1:
    st.markdown("### 🌧️ Kuraklık / İklim Baskısı")
    st.metric("Seviye", _lvl(haz))
    st.caption(f"Kuraklık bileşeni (0–1): {haz:.2f}")

    st.markdown("### 💧 Su Stresi / Maruziyet")
    st.metric("Seviye", _lvl(exp))
    st.caption(f"Maruziyet bileşeni (0–1): {exp:.2f}")

with c2:
    st.markdown("### 🐦 Tür Hassasiyeti")
    st.metric("Seviye", _lvl(sen))
    st.caption(f"Hassasiyet bileşeni (0–1): {sen:.2f}")

    st.markdown("### 🧂 Habitat Durumu ")
    if _lvl(haz) == "Yüksek" and _lvl(exp) != "Düşük":
        st.success("Kritik baskı birleşimi: kuraklık + maruziyet aynı anda yüksek/orta.")
    elif _lvl(haz) == "Düşük" and _lvl(exp) == "Düşük":
        st.info("Görece stabil koşullar: kuraklık ve maruziyet düşük.")
    else:
        st.warning("Orta düzey baskı: izleme ve hazırlık önerilir.")
    

with right:
    st.subheader("Risk Skoru ve Karar")

    st.metric("Toplam Risk (0–100)", f"{result.risk_0_100}", result.level)




    st.write("### Şu Anda Ne Yapılmalı?")

    risk = result.risk_0_100
    haz = result.components["hazard"]
    exp = result.components["exposure"]
    sen = result.components["sensitivity"]

    breeding_season = month in [4, 5, 6, 7, 8]
    actions = []

    if risk >= 70:
        st.error("🔴 ACİL MÜDAHALE GEREKLİ")
        actions += [
            "Gediz Deltası’nda çevresel akışın derhal korunması",
            "Kuraklık döneminde su çekimlerinin sınırlandırılması",
        ]
    elif risk >= 40:
        st.warning("🟠 HAZIRLIK VE YAKIN İZLEME")
        actions += [
            "Tuzluluk ve habitat değişimlerinin sıklaştırılmış izlenmesi",
            "Sulama verimliliğini artıracak kısa vadeli su yönetimi önlemleri",
        ]
    else:
        st.success("🟢 RUTİN İZLEME YETERLİ")
        actions += [
            "Rutin gözlem ve veri toplama faaliyetlerinin sürdürülmesi",
        ]

    if breeding_season and sen >= 0.7:
        actions.insert(0, "Üreme alanlarında su seviyesinin stabil tutulması")

    if exp >= 0.6 and "Sulama verimliliğini artıracak kısa vadeli su yönetimi önlemleri" not in actions:
        actions.append("Sulama verimliliğini artıracak kısa vadeli su yönetimi önlemleri")

    for a in actions:
        st.write(f"- {a}")

    st.write("### Riskin Nedenleri")

    def level_label(x: float) -> str:
        if x >= 0.7:
            return "Yüksek"
        if x >= 0.4:
            return "Orta"
        return "Düşük"

    st.markdown(f"""
- 🌧️ **Kuraklık / İklim Baskısı:** {level_label(haz)}  
  Çok yıllı kuraklık sinyallerinin şiddeti riskin ana sürücülerindendir.

- 💧 **Su Stresi ve Maruziyet:** {level_label(exp)}  
  Gediz Deltası’nın koridor üzerindeki konumu ve su stresi bu bileşeni belirler.

- 🐦 **Tür Hassasiyeti:** {level_label(sen)}  
  Seçilen türün üreme dönemi ve ekolojik gereksinimleriyle ilişkilidir.
""")

    st.write("### Neden")
    st.info(result.explanation)
st.divider()

st.write("### Sistem Yaklaşımı ve Kapsam")

st.markdown("""
Bu uygulama, **göç koridorlarını grafik tabanlı olarak modelleyen** ve
çok yıllı kuraklık sinyallerini **açıklanabilir bir risk motoru** ile
birleştiren **yapay zekâ tabanlı bir karar destek sistemidir**.

Sistem, telemetri veya düzenli sayım verisinin bulunmadığı koşullarda dahi,
**habitat güvenilirliği ve koridor darboğaz riski** üzerinden
erken uyarı ve önceliklendirme üretmek üzere tasarlanmıştır.

Üretilen risk skorları, **tehlike–maruziyet–hassasiyet** bileşenlerine
ayrıştırılarak sunulur; böylece karar vericiler için
**neden–sonuç ilişkisi şeffaf biçimde izlenebilir**.
""")


