# Ruta Earth Engine: el cubo regional satelital

**El archivo da profundidad; el satélite da frecuencia.** El cubo de detalle con fotografía aérea llega hasta 0,1–1,3 m, pero tiene pocas épocas. Earth Engine aporta un **cubo regional anual**:

| Fuente | Resolución | Desde |
|---|---|---|
| Landsat 5/7/8/9 (Collection 2, Level 2) | 30 m | 1984 |
| Sentinel-2 SR armonizado | 10 m (RGB + NIR) | 2019 (Level-2A global desde fines de 2018) |

Los dos cubos **no se mezclan píxel a píxel**. Se conectan **agregando el cubo de detalle hacia la grilla regional** (30 m o 10 m) para comparar tendencias. Nunca se remuestrea el satélite hacia abajo.

## Opción 1 · Script en Python

[`gee/cubo_regional_gee.py`](../gee/cubo_regional_gee.py) calcula una mediana anual sin nubes y exporta un COG por año a Google Drive:

```bash
pip install earthengine-api
earthengine authenticate
python gee/cubo_regional_gee.py --proyecto mi-proyecto-gcp --desde 1985 --hasta 2025
```

Cambia `AOI` por tu área. Las máscaras usan `QA_PIXEL` en Landsat y `SCL` en Sentinel-2. Si un año no tiene escenas válidas, su exportación falla: acota `--desde` y `--hasta`.

## Opción 2 · Earth Engine dentro de ArcGIS Pro

Desde ArcGIS Pro 3.2 existe el **GEE Toolbox for ArcGIS Pro**. Permite buscar y descargar datos del catálogo de Earth Engine, agregar colecciones al mapa por su identificador y usarlas en ModelBuilder o Python. Lo desarrolló Woolpert Digital Innovations, socio de Esri, y lo mantiene la comunidad: no es un producto oficial de Esri (Tanh, 2025).

## Unir ambos cubos en ArcGIS Pro

1. Descarga los COG anuales desde Drive.
2. Agrégalos a un mosaic dataset propio, con `Variable` = `landsat` o `sentinel2` y `FechaVuelo` = 1 de enero de cada año.
3. Ejecuta **Build Multidimensional Info**, como en [`arcgis-pro.md`](arcgis-pro.md).
4. Para series largas, usa **Generate Trend Raster** o **Generate Multidimensional Anomaly** (Image Analyst).

## Uso y licencias

Earth Engine es gratuito para investigación y docencia sin fines comerciales. El uso operativo de un servicio requiere un proyecto comercial (Google, 2025).

### Referencias

Google. (2025). *Earth Engine access*. Google for Developers. https://developers.google.com/earth-engine/guides/access

Tanh, L. (2025, 9 de octubre). *Bring Google Earth Engine's data right into ArcGIS Pro*. ArcGIS Blog. https://www.esri.com/arcgis-blog/products/arcgis-pro/imagery/bring-google-earth-engines-data-right-into-arcgis-pro
