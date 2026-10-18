"""Fases D y E: homogeneizar y apilar épocas ortorrectificadas en una grilla común.

Entrada: un GeoTIFF por época, YA ortorrectificado (fase C) y con su RMSE conocido.
Salida: un ráster multidimensional (tiempo, y, x) en NetCDF, con el RMSE de cada
época en los metadatos.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import rasterio
import xarray as xr
from rasterio.crs import CRS
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from .grilla import Grilla


@dataclass
class Epoca:
    etiqueta: str          # p. ej. "1994"
    fecha: str             # ISO, p. ej. "1994-01-01"; si es aproximada, dilo en 'nota'
    ruta: str              # GeoTIFF ortorrectificado (no incluido en este repositorio)
    gsd_m: float           # GSD nominal de la época
    rmse_m: float | None   # RMSE horizontal con puntos de chequeo independientes
    nota: str = ""


def remuestrear_a_grilla(ruta: str, grilla: Grilla, gsd_m: float) -> np.ndarray:
    """Lleva una época a la grilla común agregando hacia arriba (promedio).

    Si la época es más gruesa que la grilla, se detiene: eso sería inventar detalle.
    """
    if gsd_m > grilla.resolucion_m + 1e-9:
        raise ValueError(
            f"La época ({gsd_m:.2f} m) es más gruesa que la grilla "
            f"({grilla.resolucion_m:.2f} m): no se remuestrea hacia abajo."
        )
    destino = np.full((grilla.alto, grilla.ancho), np.nan, dtype="float32")
    transform = from_origin(grilla.xmin, grilla.ymax, grilla.resolucion_m, grilla.resolucion_m)
    with rasterio.open(ruta) as src:
        if src.crs is None:
            raise ValueError(f"{ruta} no tiene sistema de referencia: primero orientar y ortorrectificar.")
        reproject(
            source=rasterio.band(src, 1),
            destination=destino,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=CRS.from_epsg(grilla.epsg),
            dst_nodata=np.nan,
            resampling=Resampling.average,
        )
    return destino


def homogeneizar(capa: np.ndarray, ancla: np.ndarray | None, clahe: bool = True) -> np.ndarray:
    """Fase D: igualar histograma contra la época ancla y realzar contraste local.

    Sirve para comparar tonos entre películas y revelados distintos. No corrige
    diferencias de contenido; solo reduce el cambio de dominio radiométrico.
    """
    from skimage import exposure

    salida = capa.copy()
    valido = np.isfinite(salida)
    if not valido.any():
        return salida
    v = salida[valido]
    lo, hi = np.percentile(v, [0.5, 99.5])
    salida = np.clip((salida - lo) / max(hi - lo, 1e-6), 0, 1)
    if ancla is not None:
        va = np.isfinite(ancla)
        if va.any():
            salida[valido] = exposure.match_histograms(salida[valido], np.clip(ancla[va], 0, 1))
    if clahe:
        relleno = np.where(valido, salida, 0)
        salida = exposure.equalize_adapthist(relleno, clip_limit=0.01).astype("float32")
    salida[~valido] = np.nan
    return salida.astype("float32")


def construir_cubo(epocas: list[Epoca], grilla: Grilla, etiqueta_ancla: str | None = None,
                   homogeneizar_capas: bool = True) -> xr.DataArray:
    """Apila las épocas en un DataArray (tiempo, y, x) con exactitud declarada."""
    sin_rmse = [e.etiqueta for e in epocas if e.rmse_m is None]
    if sin_rmse:
        warnings.warn(f"Épocas sin RMSE declarado: {sin_rmse}. Sin exactitud declarada no hay cubo comparable.")

    epocas = sorted(epocas, key=lambda e: e.fecha)
    capas = {e.etiqueta: remuestrear_a_grilla(e.ruta, grilla, e.gsd_m) for e in epocas}

    if homogeneizar_capas:
        ancla_crudo = capas.get(etiqueta_ancla) if etiqueta_ancla else None
        ancla = homogeneizar(ancla_crudo, None, clahe=False) if ancla_crudo is not None else None
        capas = {k: homogeneizar(v, ancla) for k, v in capas.items()}

    r = grilla.resolucion_m
    xs = grilla.xmin + r * (np.arange(grilla.ancho) + 0.5)
    ys = grilla.ymax - r * (np.arange(grilla.alto) + 0.5)
    cubo = xr.DataArray(
        np.stack([capas[e.etiqueta] for e in epocas]),
        dims=("tiempo", "y", "x"),
        coords={
            "tiempo": np.array([e.fecha for e in epocas], dtype="datetime64[D]"),
            "y": ys,
            "x": xs,
            "etiqueta": ("tiempo", [e.etiqueta for e in epocas]),
            "gsd_m": ("tiempo", [e.gsd_m for e in epocas]),
            "rmse_m": ("tiempo", [np.nan if e.rmse_m is None else e.rmse_m for e in epocas]),
        },
        name="intensidad",
        attrs={
            "crs": f"EPSG:{grilla.epsg}",
            "resolucion_m": r,
            "ancla": etiqueta_ancla or "",
            "nota": "Cubo fotográfico pancromático; aporte temporal, no espectral. No es ARD.",
        },
    )
    return cubo


def historia_de_un_punto(cubo: xr.DataArray, x: float, y: float) -> xr.DataArray:
    """Atravesar el cubo en un punto: la serie temporal que responde '¿desde cuándo?'."""
    return cubo.sel(x=x, y=y, method="nearest")
