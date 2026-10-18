"""Validación: exactitud y área ajustada con intervalos de confianza
según buenas prácticas de Olofsson et al. (2014).

No se usa kappa como métrica principal (Pontius & Millones, 2011; Foody, 2020).
"""
from __future__ import annotations

import numpy as np


def olofsson(matriz: np.ndarray, area_mapeada: np.ndarray, z: float = 1.96) -> dict:
    """Estimadores con muestreo aleatorio estratificado por clase mapeada.

    matriz[i, j]: n.º de muestras con clase MAPEADA i y clase de REFERENCIA j.
    area_mapeada[i]: área mapeada de la clase i (cualquier unidad, p. ej. ha).
    """
    n = np.asarray(matriz, dtype=float)
    A = np.asarray(area_mapeada, dtype=float)
    if n.shape[0] != n.shape[1] or n.shape[0] != A.size:
        raise ValueError("dimensiones inconsistentes")
    A_total = A.sum()
    W = A / A_total
    n_i = n.sum(axis=1)
    if np.any(n_i < 2):
        raise ValueError("cada estrato necesita al menos 2 muestras")

    p = (W / n_i)[:, None] * n                  # proporciones de área estimadas p_ij
    p_col = p.sum(axis=0)                       # p_.j: proporción de área por clase de referencia
    global_ = np.trace(p)
    usuario = np.diag(n) / n_i
    productor = np.diag(p) / np.where(p_col > 0, p_col, np.nan)

    f = n / n_i[:, None]
    var_pj = ((W**2)[:, None] * f * (1 - f) / (n_i - 1)[:, None]).sum(axis=0)
    se_area = np.sqrt(var_pj) * A_total

    var_global = (W**2 * usuario * (1 - usuario) / (n_i - 1)).sum()
    var_usuario = usuario * (1 - usuario) / (n_i - 1)

    return {
        "exactitud_global": global_,
        "ic_global": z * np.sqrt(var_global),
        "exactitud_usuario": usuario,
        "ic_usuario": z * np.sqrt(var_usuario),
        "exactitud_productor": productor,
        "area_ajustada": p_col * A_total,
        "ic_area": z * se_area,
    }


def rmse(dx: np.ndarray, dy: np.ndarray) -> dict:
    """RMSE horizontal con puntos de chequeo independientes (≥ 30 según ASPRS, 2024)."""
    dx, dy = np.asarray(dx, float), np.asarray(dy, float)
    if dx.size < 30:
        import warnings
        warnings.warn(f"Solo {dx.size} puntos de chequeo; ASPRS (2024) exige al menos 30.")
    rx, ry = np.sqrt(np.mean(dx**2)), np.sqrt(np.mean(dy**2))
    return {"rmse_x": rx, "rmse_y": ry, "rmse_h": float(np.hypot(rx, ry)), "n": int(dx.size)}
