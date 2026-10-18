"""Pruebas de las reglas del método (sin datos reales)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cubo.cambio import filtrar_unidad_minima  # noqa: E402
from cubo.grilla import (altura_vuelo_m, desplazamiento_relieve_m, grilla_alineada,  # noqa: E402
                         gsd_m, pixel_escaneo_um, resolucion_cubo)
from cubo.validacion import olofsson  # noqa: E402


def test_pixel_1411_dpi_es_18_um():
    assert pixel_escaneo_um(1411) == pytest.approx(18.0, abs=0.01)


@pytest.mark.parametrize("escala,esperado", [(20_000, 0.36), (30_000, 0.54), (70_000, 1.26)])
def test_gsd(escala, esperado):
    assert gsd_m(1411, escala) == pytest.approx(esperado, abs=0.005)


def test_grilla_la_fija_la_epoca_mas_gruesa():
    assert resolucion_cubo([0.36, 0.40, 0.54, 1.08, 1.26]) == pytest.approx(1.3)


def test_relieve():
    assert altura_vuelo_m(153, 20_000) == pytest.approx(3060)
    assert desplazamiento_relieve_m(10, 100, 153, 20_000) == pytest.approx(65.4, abs=0.1)


def test_grilla_alineada():
    g = grilla_alineada(100.4, 200.2, 110.1, 205.0, 1.3, 32719)
    for v in (g.xmin, g.ymin, g.xmax, g.ymax):
        assert math.isclose(v / 1.3, round(v / 1.3), abs_tol=1e-9)


def test_unidad_minima():
    m = np.zeros((100, 100), bool)
    m[0:2, 0:2] = True          # 4 px = 4 m² → se elimina
    m[50:80, 50:80] = True      # 900 px = 900 m² → se mantiene con UMM 0,05 ha
    out = filtrar_unidad_minima(m, 1.0, umm_ha=0.05)
    assert not out[0, 0] and out[60, 60]


def test_olofsson_ejemplo_publicado():
    # Ejemplo numérico de Olofsson et al. (2014, tabla 8).
    n = np.array([[66, 0, 5, 4], [0, 55, 8, 12], [1, 0, 153, 11], [2, 1, 9, 313]])
    A = np.array([200_000, 150_000, 3_200_000, 6_450_000])
    r = olofsson(n, A)
    assert r["exactitud_global"] == pytest.approx(0.947, abs=0.001)
    assert r["area_ajustada"][0] == pytest.approx(235_086, rel=0.002)
    assert r["ic_area"][0] == pytest.approx(68_418, rel=0.01)
