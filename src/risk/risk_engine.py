from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict
import numpy as np
import networkx as nx

CDILevel = Literal["none", "watch", "warning", "alert"]

@dataclass(frozen=True)
class DroughtSignals:
    spi12: float
    spi24: float
    cdi: CDILevel

@dataclass(frozen=True)
class RiskResult:
    risk_0_100: float
    level: Literal["Watch", "Warning", "Alert"]
    components: Dict[str, float]
    explanation: str
    actions: list[str]

def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

def drought_hazard(signals: DroughtSignals) -> float:
    def spi_to_h(spi: float) -> float:
        if spi >= 0:
            return 0.0
        return _clamp01(abs(spi) / 3.0)

    h_spi = 0.45 * spi_to_h(signals.spi12) + 0.45 * spi_to_h(signals.spi24)
    cdi_boost = {"none": 0.0, "watch": 0.15, "warning": 0.30, "alert": 0.45}[signals.cdi]
    return _clamp01(h_spi + cdi_boost)

def exposure_from_graph(G_species: nx.DiGraph, node: str, base_water_stress: float) -> float:
    btw = nx.betweenness_centrality(G_species).get(node, 0.0)
    return _clamp01(0.55 * btw + 0.45 * _clamp01(base_water_stress))

def species_sensitivity(species: str, month: int) -> float:
    species = species.lower()
    if species == "flamingo":
        if month in [6, 7]:
            return 0.90
        if month in [4, 5, 8]:
            return 0.70
        return 0.40
    if species == "pelican":
        if month == 6:
            return 0.90
        if month in [5, 7]:
            return 0.75
        return 0.45
    return 0.50

def risk_level(risk_0_100: float) -> Literal["Watch", "Warning", "Alert"]:
    if risk_0_100 >= 80:
        return "Alert"
    if risk_0_100 >= 60:
        return "Warning"
    return "Watch"

def recommended_actions(level: str) -> list[str]:
    if level == "Alert":
        return [
            "Kritik dönemde (özellikle Haz–Ağu) çevresel akış/su seviyesi stabilizasyonu için acil koordinasyon.",
            "Gediz’de üreme ve beslenme alanlarında hızlı saha kontrolü: su seviyesi, tuzluluk, erişilebilir sığ alanlar.",
            "Hızlandırılmış izleme: haftalık durum raporu + risk göstergeleri (SPI/CDI) ile eşleştirme.",
        ]
    if level == "Warning":
        return [
            "Su çekimleri ve akış rejimi açısından Haz–Ağu çatışmasına yönelik önleyici plan (sulama verimliliği/planlama).",
            "Kritik habitat parçalarında (sığ alanlar/tatlı su bataklıkları) koruma önlemleri ve erişim yönetimi.",
            "Gözlem sinyali toplama (yerel gözlem/eBird vb.) ile risk skorunu kalibre etmeye başlama.",
        ]
    return [
        "Kuraklık sinyallerini (SPI/CDI) aylık takip; eşik aşımı durumunda Warning protokolüne geç.",
        "Koridor düğümlerinde (Gediz/Kerkini/Tuz) temel izleme planını hazır tut.",
        "Veri entegrasyon planı: ileride sayım/telemetri gelirse modele bağlanacak şekilde kayıt standartları oluştur.",
    ]

def compute_risk(
    G_species: nx.DiGraph,
    species: str,
    node: str,
    month: int,
    signals: DroughtSignals,
    base_water_stress: float = 0.9,
    weights: dict[str, float] | None = None,
) -> RiskResult:
    if weights is None:
        weights = {"hazard": 0.45, "exposure": 0.35, "sensitivity": 0.20}

    h = drought_hazard(signals)
    e = exposure_from_graph(G_species, node=node, base_water_stress=base_water_stress)
    s = species_sensitivity(species, month=month)

    r01 = _clamp01(weights["hazard"] * h + weights["exposure"] * e + weights["sensitivity"] * s)
    r100 = float(np.round(r01 * 100.0, 1))
    lvl = risk_level(r100)
    acts = recommended_actions(lvl)

    cdi_map = {"none": "CDI: yok", "watch": "CDI: Watch", "warning": "CDI: Warning", "alert": "CDI: Alert"}
    explanation = (
        f"Risk {lvl} çünkü: kuraklık göstergeleri (SPI-12={signals.spi12}, SPI-24={signals.spi24}, {cdi_map[signals.cdi]}) "
        f"tehlike katkısını yükseltiyor; {node} düğümü koridor içinde darboğaz etkisi taşıyor; "
        f"ay={month} tür hassasiyet penceresiyle çakışıyor (species={species})."
    )

    return RiskResult(
        risk_0_100=r100,
        level=lvl,
        components={"hazard": h, "exposure": e, "sensitivity": s},
        explanation=explanation,
        actions=acts,
    )
