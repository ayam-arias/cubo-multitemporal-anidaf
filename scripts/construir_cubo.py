"""Construye el cubo a partir de una configuración YAML.

Uso:
    python scripts/construir_cubo.py config/mis_epocas.yaml
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cubo.apilar import Epoca, construir_cubo          # noqa: E402
from cubo.grilla import gsd_m, grilla_alineada, resolucion_cubo  # noqa: E402


def main(ruta_cfg: str) -> None:
    cfg = yaml.safe_load(Path(ruta_cfg).read_text(encoding="utf-8"))
    dpi = cfg["escaneo_dpi"]
    epocas = [
        Epoca(etiqueta=str(e["etiqueta"]), fecha=e["fecha"], ruta=e["ruta"],
              gsd_m=gsd_m(dpi, e["escala"]), rmse_m=e.get("rmse_m"), nota=e.get("nota", ""))
        for e in cfg["epocas"]
    ]
    for e in epocas:
        print(f"{e.etiqueta}: GSD {e.gsd_m:.2f} m  ·  RMSE {e.rmse_m if e.rmse_m is not None else 'SIN DECLARAR'}")

    g = cfg["grilla"]
    res = g.get("resolucion_m") or resolucion_cubo([e.gsd_m for e in epocas])
    grilla = grilla_alineada(*g["extension"], resolucion_m=res, epsg=g["epsg"])
    print(f"Grilla común: {res:.2f} m · {grilla.ancho} × {grilla.alto} celdas · EPSG:{grilla.epsg}")

    cubo = construir_cubo(epocas, grilla, etiqueta_ancla=str(cfg.get("ancla")))
    salida = Path(cfg.get("salida", "salidas/cubo.nc"))
    salida.parent.mkdir(parents=True, exist_ok=True)
    cubo.to_netcdf(salida)
    print(f"Cubo guardado en {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
