# Cubo multitemporal con fotografía aérea histórica

**Del archivo que se consulta al cubo que se mide.**

Metodología y código abierto para ordenar décadas de fotografía aérea en un **cubo de datos** (tiempo, y, x) y detectar cambios territoriales con exactitud declarada. Acompaña dos ponencias del 23 de octubre de 2026:

- *Detección multitemporal de cambios territoriales: un cubo de datos con cuatro décadas de fotografía aérea del archivo ANIDAF* (Seminario GeoIA, Instituto Geográfico Militar, con Esri Chile).
- *Del archivo histórico a la decisión: avión, satélite y dron sobre el archivo ANIDAF para la fiscalización ambiental del territorio* (Simposio Tecnologías Aerotransportadas, Servicio Aerofotogramétrico – Duoc UC).

Presentaciones, referencias y contacto: **[linktr.ee/geoian](https://linktr.ee/geoian)**.

> **Este repositorio no contiene datos.** Solo describe el método e incluye código para aplicarlo a tus propias ortofotos. Las imágenes del Archivo Nacional de Imágenes Aéreas (ANIDAF) se solicitan al [Servicio Aerofotogramétrico](https://www.saf.cl/productos/anidaf/).

---

## Simulador interactivo

👉 **[Abrir el simulador](https://ayam-arias.github.io/cubo-multitemporal-anidaf/)** (`docs/index.html`): un cubo de cinco épocas que se puede atravesar en un punto, con detección de cambios, error de registro y homogeneización, y con su equivalente paso a paso en **Python** y en **ArcGIS Pro**.

> Simulación con datos sintéticos generados en el navegador, solo para graficar el concepto. No son fotogramas del archivo ANIDAF ni resultados de un modelo.

## ¿Qué es un cubo de datos?

Muchas fotos del mismo lugar, **en la misma grilla, ordenadas en el tiempo**. X e Y dicen dónde; T dice cuándo. Atravesar el cubo en un punto entrega su historia completa y responde la pregunta clave: **¿desde cuándo?**

La condición es que todas las capas calcen: mismo sistema de referencia, misma extensión, mismo tamaño de píxel y grilla alineada. Si no, no es un cubo: es una pila de imágenes.

## Avión, satélite y dron en el mismo cubo

Cada plataforma aerotransportada responde una pregunta distinta; el cubo las pone en la misma grilla.

| Plataforma | Pregunta | Resolución típica | Rol en el cubo |
|---|---|---|---|
| **Avión** (archivo ANIDAF, 1945–2010) | ¿Desde cuándo? | ≈1,26 m (18 µm × 1:70.000) | Línea base histórica |
| **Satélite** (Landsat, Sentinel-2, FASat-Delta) | ¿Dónde cambió? | 30 m a 0,72 m | Serie anual regional |
| **Dron** (RPAS) | ¿Cuánto, exactamente? | ≈3 cm a 100 m | Verificación local actual |

Para combinarlas se agrega el detalle hacia la resolución común del cubo (regla 1). El dron no se degrada para la medición local: se usa como verdad de terreno para validar el cambio detectado.

## El método en seis fases

```
A Inventario → B Orientación → C Ortorrectificación → D Homogeneización → E Cubo → F Cambio
```

La fase C decide el proyecto: **sin exactitud declarada no hay cubo comparable**. El detalle de cada fase está en [`docs/metodologia.md`](docs/metodologia.md).

Tres reglas que no se negocian:

1. **El cubo no es más fino que su época más gruesa.** GSD = píxel de escaneo × escala (18 µm × 70.000 = 1,26 m). Se agrega hacia arriba; nunca se inventa detalle.
2. **Georreferenciar no basta: se ortorrectifica con DEM.** El relieve desplaza la foto (`d = r · h / H`).
3. **La exactitud se declara y el área se valida.** RMSE con ≥ 30 puntos de chequeo (ASPRS, 2024); área ajustada con IC 95 % (Olofsson et al., 2014).

## Tres rutas al mismo cubo

| Ruta | Para quién | Guía |
|---|---|---|
| **ArcGIS Pro** | Analistas SIG, sin programar: Ortho Mapping, ráster multidimensional, Change Detection Wizard y aprendizaje profundo | [`docs/arcgis-pro.md`](docs/arcgis-pro.md) · [`arcgis/cubo_arcpy.py`](arcgis/cubo_arcpy.py) |
| **Python abierto** | Investigación y automatización con rasterio, xarray y scikit-image | este README · [`cubo/`](cubo/) |
| **Google Earth Engine** | Cubo regional anual con Landsat y Sentinel-2, también desde ArcGIS Pro con el GEE Toolbox | [`docs/earth-engine.md`](docs/earth-engine.md) · [`gee/cubo_regional_gee.py`](gee/cubo_regional_gee.py) |

Las tres rutas siguen las mismas seis fases y las mismas reglas. Cambia la herramienta, no el método.

## Estructura

```
cubo/
  grilla.py      GSD, altura de vuelo, desplazamiento por relieve, grilla alineada
  registro.py    registro automático SIFT + RANSAC contra la época ancla (apoyo a la fase B)
  apilar.py      homogeneización y construcción del cubo (NetCDF) con RMSE por época
  cambio.py      dónde cambió: diferencia + Otsu + unidad mínima de mapeo
  validacion.py  RMSE y estimadores de Olofsson et al. (2014)
scripts/
  construir_cubo.py   construye el cubo desde una configuración YAML
config/
  epocas_plantilla.yaml
arcgis/
  cubo_arcpy.py       mosaico multidimensional y diferencia entre épocas con arcpy
gee/
  cubo_regional_gee.py  compuestos anuales Landsat y Sentinel-2 exportados como COG
docs/
  metodologia.md      las seis fases en detalle
  arcgis-pro.md       ruta ArcGIS Pro paso a paso
  earth-engine.md     ruta Earth Engine y unión de ambos cubos
tests/
  test_metodo.py      verifica las reglas con valores publicados (sin datos)
```

## Uso

```bash
git clone https://github.com/ayam-arias/cubo-multitemporal-anidaf
cd cubo-multitemporal-anidaf
pip install -r requirements.txt
python -m pytest -q                      # comprueba las reglas del método

cp config/epocas_plantilla.yaml config/mis_epocas.yaml
# edita rutas, escalas, RMSE y extensión de TUS ortofotos
python scripts/construir_cubo.py config/mis_epocas.yaml
```

Leer el cubo y la historia de un punto:

```python
import xarray as xr
from cubo.apilar import historia_de_un_punto
from cubo.cambio import mascara_cambio, area_ha

cubo = xr.open_dataarray("salidas/cubo.nc")
print(historia_de_un_punto(cubo, x=270_100, y=6_370_200).values)

m, umbral = mascara_cambio(cubo[0].values, cubo[-1].values, resolucion_m=cubo.attrs["resolucion_m"])
print(f"Cambio detectado: {area_ha(m, cubo.attrs['resolucion_m']):.1f} ha")
```

¿Prefieres no programar? Sigue la ruta de [ArcGIS Pro](docs/arcgis-pro.md).

## Límites

- **Inferencia no es evidencia:** la superresolución y la colorización inventan detalle; nunca se usan para medir.
- **El modelo hereda el sesgo** de quien etiqueta: lo que propone, el fotogrametrista lo verifica.
- Es un cubo fotográfico pancromático: su aporte es **temporal**, no espectral.

## Referencias principales

- American Society for Photogrammetry and Remote Sensing. (2024). *ASPRS positional accuracy standards for digital geospatial data* (Edition 2, Version 2).
- Foody, G. M. (2020). Explaining the unsuitability of the kappa coefficient in the assessment and comparison of the accuracy of thematic maps obtained by image classification. *Remote Sensing of Environment, 239*, 111630. https://doi.org/10.1016/j.rse.2019.111630
- Knuth, F., Shean, D., Bhushan, S., Schwat, E., Alexandrov, O., McNeil, C., Dehecq, A., Florentine, C., & O'Neel, S. (2023). Historical Structure from Motion (HSfM). *Remote Sensing of Environment, 285*, 113379. https://doi.org/10.1016/j.rse.2022.113379
- Mahecha, M. D., Gans, F., Brandt, G., Christiansen, R., Cornell, S. E., … Reichstein, M. (2020). Earth system data cubes unravel global multivariate dynamics. *Earth System Dynamics, 11*(1), 201–234. https://doi.org/10.5194/esd-11-201-2020
- Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment, 148*, 42–57. https://doi.org/10.1016/j.rse.2014.02.015
- Otsu, N. (1979). A threshold selection method from gray-level histograms. *IEEE Transactions on Systems, Man, and Cybernetics, 9*(1), 62–66. https://doi.org/10.1109/TSMC.1979.4310076
- Pontius, R. G., Jr., & Millones, M. (2011). Death to Kappa. *International Journal of Remote Sensing, 32*(15), 4407–4429. https://doi.org/10.1080/01431161.2011.552923
- Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image segmentation. En *MICCAI 2015* (pp. 234–241). Springer. https://doi.org/10.1007/978-3-319-24574-4_28

La lista completa está en la carpeta de referencias enlazada en [linktr.ee/geoian](https://linktr.ee/geoian).

## Autor y contacto

**Ian Franco Arias Carrasco** · Geomática, fotogrametría y GeoIA
Presentación, referencias y contacto: [linktr.ee/geoian](https://linktr.ee/geoian)

Código bajo licencia MIT. Si usas el método, cítalo con [`CITATION.cff`](CITATION.cff).
