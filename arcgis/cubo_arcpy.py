"""Fase E y F en ArcGIS Pro con arcpy.

Arma un ráster multidimensional (mosaic dataset) a partir de ortofotos por época
y calcula la diferencia entre dos épocas. Ejecutar en la ventana de Python de
ArcGIS Pro o en un Notebook de ArcGIS Pro.

Requisitos: ArcGIS Pro 3.x; extensión Image Analyst para arcpy.ia.
Este repositorio NO incluye datos: edita las rutas de EPOCAS con tus ortofotos,
ya remuestreadas a la grilla común (mismo SRC, tamaño de píxel y Snap Raster).
"""
import datetime as dt
import os

import arcpy

# ---------------------------------------------------------------- configuración
GDB = r"C:\cubo\cubo.gdb"                 # se crea si no existe
MOSAICO = "cubo_anidaf"
SRC = arcpy.SpatialReference(32719)       # WGS 84 / UTM 19S
EPOCAS = [
    # (etiqueta, fecha, ruta ortofoto en grilla común, RMSE en m)
    ("1980", dt.datetime(1980, 1, 1), r"C:\cubo\orto\orto_1980.tif", None),
    ("1994", dt.datetime(1994, 1, 1), r"C:\cubo\orto\orto_1994.tif", None),
    ("2005", dt.datetime(2005, 1, 1), r"C:\cubo\orto\orto_2005.tif", None),
]
DESDE, HASTA = "1980", "2005"             # épocas a comparar
# ------------------------------------------------------------------------------

arcpy.env.overwriteOutput = True

if not arcpy.Exists(GDB):
    arcpy.management.CreateFileGDB(os.path.dirname(GDB), os.path.basename(GDB))
md = os.path.join(GDB, MOSAICO)

# 1. Mosaic dataset de una banda
arcpy.management.CreateMosaicDataset(GDB, MOSAICO, SRC, 1)

# 2. Agregar las épocas
arcpy.management.AddRastersToMosaicDataset(
    md, "Raster Dataset", [e[2] for e in EPOCAS],
    calculate_statistics="CALCULATE_STATISTICS",
)

# 3. Campos de variable, fecha, etiqueta y exactitud declarada
for nombre, tipo in (("Variable", "TEXT"), ("FechaVuelo", "DATE"),
                     ("Epoca", "TEXT"), ("RMSE_m", "DOUBLE")):
    arcpy.management.AddField(md, nombre, tipo)

por_archivo = {os.path.splitext(os.path.basename(r))[0].lower(): (et, f, rmse)
               for et, f, r, rmse in EPOCAS}
with arcpy.da.UpdateCursor(md, ["Name", "Variable", "FechaVuelo", "Epoca", "RMSE_m"]) as cur:
    for fila in cur:
        et, fecha, rmse = por_archivo[fila[0].lower()]
        cur.updateRow([fila[0], "intensidad", fecha, et, rmse])

sin_rmse = [e[0] for e in EPOCAS if e[3] is None]
if sin_rmse:
    arcpy.AddWarning(f"Épocas sin RMSE declarado: {sin_rmse}. Sin exactitud declarada no hay cubo comparable.")

# 4. Metadatos multidimensionales: variable 'intensidad', dimensión 'FechaVuelo'
arcpy.md.BuildMultidimensionalInfo(md, "Variable", [["FechaVuelo", "Fecha del vuelo", ""]])

# 5. Diferencia entre dos épocas (nivel 1: dónde cambió)
arcpy.CheckOutExtension("ImageAnalyst")
ruta = {e[0]: e[2] for e in EPOCAS}
dif = arcpy.ia.ComputeChange(arcpy.Raster(ruta[DESDE]), arcpy.Raster(ruta[HASTA]), "DIFFERENCE")
salida = os.path.join(GDB, f"dif_{DESDE}_{HASTA}")
dif.save(salida)
print(f"Cubo: {md}\nDiferencia: {salida}")
print("Siguiente paso: umbral en el Change Detection Wizard o Otsu en cubo/cambio.py; "
      "luego filtrar la unidad mínima de mapeo.")
