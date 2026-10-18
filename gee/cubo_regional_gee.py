"""Cubo regional anual con Google Earth Engine (Landsat 1984–hoy + Sentinel-2 2019–hoy).

Complementa el cubo de detalle con fotografía aérea: el archivo da profundidad,
el satélite da frecuencia. Exporta un compuesto anual (mediana sin nubes) por año
como GeoTIFF optimizado (COG) a Google Drive. Después se carga en el mosaico
multidimensional de ArcGIS Pro (docs/arcgis-pro.md) o con xarray.

Requisitos:
    pip install earthengine-api
    earthengine authenticate
    Proyecto de Google Cloud registrado en Earth Engine. El uso no comercial
    (investigación, docencia) es gratuito; el uso operativo de un servicio
    requiere proyecto comercial.

Uso:
    python gee/cubo_regional_gee.py --proyecto mi-proyecto-gcp --desde 1985 --hasta 2025
"""
import argparse

import ee

# Área de ejemplo: corredor Puchuncaví–Quintero–Horcón–Ritoque (lon/lat, WGS 84). Cámbiala por la tuya.
AOI = [-71.56, -32.86, -71.40, -32.69]
EPSG = "EPSG:32719"


def mascara_landsat(img):
    """Máscara de nubes, sombras y nubes dilatadas (QA_PIXEL, Collection 2) y factores de escala."""
    qa = img.select("QA_PIXEL")
    limpio = qa.bitwiseAnd(0b11010).eq(0)  # bits 1 (nube dilatada), 3 (nube), 4 (sombra)
    sr = img.select("SR_B.").multiply(0.0000275).add(-0.2)
    return img.addBands(sr, None, True).updateMask(limpio)


def landsat_anual(anio, aoi):
    """Mediana anual de Landsat 5/7/8/9 Collection 2 Level 2, bandas armonizadas RGB+NIR."""
    ini, fin = f"{anio}-01-01", f"{anio}-12-31"
    tm = ["SR_B1", "SR_B2", "SR_B3", "SR_B4"]   # L5, L7: azul, verde, rojo, NIR
    oli = ["SR_B2", "SR_B3", "SR_B4", "SR_B5"]  # L8, L9
    nombres = ["azul", "verde", "rojo", "nir"]

    def col(id_, bandas):
        return (ee.ImageCollection(id_).filterBounds(aoi).filterDate(ini, fin)
                .map(mascara_landsat).select(bandas, nombres))

    coleccion = (col("LANDSAT/LT05/C02/T1_L2", tm)
                 .merge(col("LANDSAT/LE07/C02/T1_L2", tm))
                 .merge(col("LANDSAT/LC08/C02/T1_L2", oli))
                 .merge(col("LANDSAT/LC09/C02/T1_L2", oli)))
    return coleccion.median().clip(aoi).set("anio", anio, "sensor", "Landsat")


def sentinel2_anual(anio, aoi):
    """Mediana anual de Sentinel-2 SR armonizado con máscara SCL."""
    def mascara(img):
        scl = img.select("SCL")
        limpio = scl.remap([4, 5, 6, 7, 11], [1, 1, 1, 1, 1], 0)  # vegetación, suelo, agua, s/clasif., nieve
        return img.select(["B2", "B3", "B4", "B8"], ["azul", "verde", "rojo", "nir"]) \
                  .divide(10000).updateMask(limpio)

    coleccion = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(aoi)
                 .filterDate(f"{anio}-01-01", f"{anio}-12-31").map(mascara))
    return coleccion.median().clip(aoi).set("anio", anio, "sensor", "Sentinel-2")


def exportar(img, nombre, escala, aoi, carpeta):
    tarea = ee.batch.Export.image.toDrive(
        image=img.toFloat(), description=nombre, folder=carpeta, fileNamePrefix=nombre,
        region=aoi, scale=escala, crs=EPSG, maxPixels=1e10,
        formatOptions={"cloudOptimized": True},
    )
    tarea.start()
    print(f"Exportando {nombre} ({escala} m)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proyecto", required=True, help="ID del proyecto de Google Cloud")
    ap.add_argument("--desde", type=int, default=1985)
    ap.add_argument("--hasta", type=int, default=2025)
    ap.add_argument("--carpeta", default="cubo_regional")
    a = ap.parse_args()

    ee.Initialize(project=a.proyecto)
    aoi = ee.Geometry.Rectangle(AOI)
    for anio in range(a.desde, a.hasta + 1):
        exportar(landsat_anual(anio, aoi), f"landsat_{anio}", 30, aoi, a.carpeta)
        if anio >= 2019:  # Level-2A con cobertura global desde fines de 2018
            exportar(sentinel2_anual(anio, aoi), f"sentinel2_{anio}", 10, aoi, a.carpeta)
    print("Revisa el avance en https://code.earthengine.google.com/tasks")


if __name__ == "__main__":
    main()
