"""Fase B (apoyo): registro automático de una época contra la época ancla.

SIFT + RANSAC con OpenCV. Útil para afinar el calce entre épocas ya
ortorrectificadas o para proponer puntos homólogos. NO reemplaza la
ortorrectificación con DEM: una transformación 2D no corrige el relieve.
"""
from __future__ import annotations

import numpy as np


def a_uint8(img: np.ndarray) -> np.ndarray:
    v = img[np.isfinite(img)]
    lo, hi = np.percentile(v, [1, 99]) if v.size else (0, 1)
    out = np.clip((np.nan_to_num(img, nan=lo) - lo) / max(hi - lo, 1e-6), 0, 1)
    return (out * 255).astype("uint8")


def registrar_sift(movil: np.ndarray, ancla: np.ndarray, ratio: float = 0.75,
                   umbral_ransac_px: float = 3.0) -> dict:
    """Estima una transformación afín parcial (rotación, escala, traslación)."""
    import cv2

    a, b = a_uint8(movil), a_uint8(ancla)
    sift = cv2.SIFT_create()
    kp1, d1 = sift.detectAndCompute(a, None)
    kp2, d2 = sift.detectAndCompute(b, None)
    if d1 is None or d2 is None:
        raise RuntimeError("sin rasgos suficientes")
    pares = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    buenos = [m for m, n in (p for p in pares if len(p) == 2) if m.distance < ratio * n.distance]
    if len(buenos) < 10:
        raise RuntimeError(f"solo {len(buenos)} correspondencias; revisar a mano")
    src = np.float32([kp1[m.queryIdx].pt for m in buenos])
    dst = np.float32([kp2[m.trainIdx].pt for m in buenos])
    M, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                             ransacReprojThreshold=umbral_ransac_px)
    inl = inliers.ravel().astype(bool)
    resid = cv2.transform(src[inl][None], M)[0] - dst[inl]
    return {"matriz": M, "n_inliers": int(inl.sum()), "n_pares": len(buenos),
            "rmse_px": float(np.sqrt((resid**2).sum(axis=1).mean()))}
