"""Fase E (preparación): tamaño de píxel y grilla común del cubo.

Regla central: el cubo no puede ser más fino que su época más gruesa.
Remuestrear hacia arriba inventa detalle; solo se agrega hacia abajo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MICRONES_POR_PULGADA = 25_400


def pixel_escaneo_um(dpi: float) -> float:
    """Tamaño del píxel de escaneo en micrones (1.411 dpi ≈ 18 µm)."""
    if dpi <= 0:
        raise ValueError("dpi debe ser positivo")
    return MICRONES_POR_PULGADA / dpi


def gsd_m(dpi: float, denominador_escala: float) -> float:
    """GSD nominal en metros = píxel de escaneo × denominador de escala.

    Ej.: 18 µm × 20.000 = 0,36 m. Es GSD, no resolución efectiva:
    la película y la óptica la limitan.
    """
    return pixel_escaneo_um(dpi) * 1e-6 * denominador_escala


def altura_vuelo_m(focal_mm: float, denominador_escala: float) -> float:
    """H = f × E (f = 153 mm a 1:20.000 → 3.060 m)."""
    return focal_mm * 1e-3 * denominador_escala


def desplazamiento_relieve_m(r_foto_cm: float, h_m: float, focal_mm: float,
                             denominador_escala: float) -> float:
    """Desplazamiento por relieve en terreno: d = r · h / H.

    r se mide en la foto (cm) y se lleva a terreno con la escala.
    Muestra por qué georreferenciar en 2D no basta: hay que ortorrectificar con DEM.
    """
    H = altura_vuelo_m(focal_mm, denominador_escala)
    r_terreno = r_foto_cm * 1e-2 * denominador_escala
    return r_terreno * h_m / H


@dataclass(frozen=True)
class Grilla:
    resolucion_m: float
    epsg: int
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def ancho(self) -> int:
        return int(round((self.xmax - self.xmin) / self.resolucion_m))

    @property
    def alto(self) -> int:
        return int(round((self.ymax - self.ymin) / self.resolucion_m))


def resolucion_cubo(gsds_m: list[float], redondeo_m: float = 0.1) -> float:
    """Resolución de la grilla: la época más gruesa, redondeada hacia arriba."""
    if not gsds_m:
        raise ValueError("se necesita al menos una época")
    peor = max(gsds_m)
    return math.ceil(peor / redondeo_m - 1e-9) * redondeo_m


def grilla_alineada(xmin: float, ymin: float, xmax: float, ymax: float,
                    resolucion_m: float, epsg: int) -> Grilla:
    """Ajusta la extensión a múltiplos de la resolución (target-aligned pixels),
    para que todas las épocas caigan exactamente en las mismas celdas."""
    r = resolucion_m
    return Grilla(
        resolucion_m=r,
        epsg=epsg,
        xmin=math.floor(xmin / r) * r,
        ymin=math.floor(ymin / r) * r,
        xmax=math.ceil(xmax / r) * r,
        ymax=math.ceil(ymax / r) * r,
    )
