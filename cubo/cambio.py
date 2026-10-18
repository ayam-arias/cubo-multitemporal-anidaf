"""Fase F (nivel 1, no supervisado): dónde cambió.

Diferencia entre épocas homogeneizadas + umbral automático de Otsu (1979)
+ unidad mínima de mapeo. Es el resultado mínimo garantizado: no requiere etiquetas.
El nivel 2 (qué cambió: U-Net, redes siamesas) se describe en docs/metodologia.md.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def umbral_otsu(valores: np.ndarray) -> float:
    from skimage.filters import threshold_otsu

    v = valores[np.isfinite(valores)]
    if v.size == 0:
        raise ValueError("sin valores válidos")
    return float(threshold_otsu(v))


def filtrar_unidad_minima(mascara: np.ndarray, resolucion_m: float, umm_ha: float = 0.5) -> np.ndarray:
    """Elimina parches menores que la unidad mínima de mapeo (en hectáreas)."""
    pix_min = int(np.ceil(umm_ha * 10_000 / resolucion_m**2))
    etiquetas, n = ndimage.label(mascara, structure=np.ones((3, 3)))
    if n == 0:
        return mascara.astype(bool)
    tamanos = ndimage.sum(mascara, etiquetas, index=np.arange(1, n + 1))
    conservar = np.zeros(n + 1, dtype=bool)
    conservar[1:] = tamanos >= pix_min
    return conservar[etiquetas]


def mascara_cambio(antes: np.ndarray, despues: np.ndarray, resolucion_m: float,
                   umm_ha: float = 0.5) -> tuple[np.ndarray, float]:
    """Devuelve la máscara de cambio y el umbral usado."""
    dif = np.abs(despues.astype("float32") - antes.astype("float32"))
    t = umbral_otsu(dif)
    mascara = np.where(np.isfinite(dif), dif > t, False)
    return filtrar_unidad_minima(mascara, resolucion_m, umm_ha), t


def area_ha(mascara: np.ndarray, resolucion_m: float) -> float:
    return float(mascara.sum()) * resolucion_m**2 / 10_000
