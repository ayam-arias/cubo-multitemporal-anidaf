# Ruta ArcGIS Pro: el mismo cubo, sin programar

Esta guía replica las seis fases de [`metodologia.md`](metodologia.md) con herramientas de ArcGIS Pro. El concepto de ArcGIS que corresponde a nuestro cubo es el **ráster multidimensional** (variable × dimensión tiempo). No es un *Space Time Cube*, que en ArcGIS se usa para puntos y eventos.

**Requisitos:** ArcGIS Pro 3.x con la extensión **Image Analyst** (detección de cambios y aprendizaje profundo). Antes de empezar, confirma con tu distribuidor qué nivel de licencia exige Ortho Mapping en tu versión.

---

## A · Inventario

1. Arma dos tablas, en CSV o como tablas de geodatabase:
   - **Cameras**: focal, coordenadas de las marcas fiduciales en micrones (desde el certificado de calibración) y tamaño del formato.
   - **Frames**: ruta de cada fotograma escaneado, cámara asociada y, si existe, la posición aproximada.
2. Otra opción es usar la herramienta **Build Frame and Camera Tables**.
3. Convierte los escaneos a COG (*Raster to Other Format* o *Copy Raster*) para trabajar más rápido.

## B · Orientación

1. **Imagery → New Workspace → Ortho Mapping**. Tipo: **Aerial – Scanned**.
2. En *Data Loader Options*, carga las tablas Cameras y Frames y elige un **DEM** (por ejemplo, Copernicus GLO-30 o World Elevation).
3. Mide las marcas fiduciales con **Refine Interior Orientation**:
   - si conoces sus coordenadas (certificado de calibración), captura una plantilla y aplica;
   - si no las conoces, captura las 8 (centrales y esquinas) en una imagen.

Trabaja una época por espacio de trabajo. Empieza por la **época ancla**.

## C · Ortorrectificación y exactitud

1. Pulsa **Adjust** (aerotriangulación). La primera corrida genera los puntos de enlace y la orientación relativa. Revisa el resultado en el *Tie Point Editor*.
2. Agrega puntos de control en el **GCP Manager**, sobre rasgos estables (construcciones antiguas, cruces de caminos, muelles), y nunca sobre costa, vegetación ni cauces.
3. Marca una parte de los puntos como **Check Points**. Esos puntos no entran al ajuste y sirven para medir el **RMSE**. ASPRS (2024) exige al menos 30.
4. Ejecuta el ajuste de nuevo con los puntos de control.
5. En **Multiple Products**, elige *Orthorectify Images* y luego genera la ortofoto con *Orthomosaic*.
6. Anota el RMSE de cada época: debe acompañar al cubo.

Esri publica un flujo específico para fotografía histórica escaneada (Esri, s. f.-a).

## D · Homogeneización

Aplica a cada ortofoto una cadena de **funciones ráster**:

- *Stretch* (percentiles 0,5–99,5 %) para normalizar el tono;
- un estiramiento con las **estadísticas de la época ancla** (*Stretch* con estadísticas personalizadas), para que todas compartan el mismo rango tonal.

Guarda la cadena como **plantilla de funciones ráster**, para aplicar lo mismo a todas las épocas.

## E · El cubo: ráster multidimensional

Primero define la grilla común. Todas las épocas deben salir con el **mismo sistema de coordenadas, tamaño de píxel y alineación**. En *Environments* fija *Output Coordinate System*, *Cell Size* (la época más gruesa, por ejemplo 1,3 m) y *Snap Raster*. Lleva cada época a esa grilla con **Aggregate** (*Mean*), que agrega hacia arriba sin inventar detalle. Si el factor no es entero, usa **Resample** (*Bilinear*). Nunca bajes a un píxel más fino que el de la época.

Luego arma el cubo (Esri, s. f.-b):

1. **Create Mosaic Dataset** (1 banda).
2. **Add Rasters To Mosaic Dataset** con el tipo *Raster Dataset*. Marca *Calculate Statistics*.
3. En la tabla de *Footprint*, crea:
   - `Variable` (texto) = `intensidad`;
   - `FechaVuelo` (fecha), con la fecha de cada época;
   - `RMSE_m` (doble), para dejar la exactitud declarada junto a cada capa.
4. Ejecuta **Build Multidimensional Info** con *Variable Field* = `Variable` y *Dimension Fields* = `FechaVuelo`.
5. Agrega el mosaico al mapa. La pestaña **Multidimensional** permite recorrer las épocas con el control de tiempo.

Para guardar un cubo autocontenido, usa **Copy Raster** a formato **CRF** con *Process as Multidimensional* activado.

## F · Cambio

**Nivel 1, dónde cambió (sin entrenar):**

1. Selecciona el ráster multidimensional y abre **Imagery → Change Detection → Change Detection Wizard**.
2. Método: **Pixel Value Change**. Elige la variable, la época *From* y la época *To*.
3. Usa *Difference Type* = **Absolute**.
4. En *Classify Difference*, ajusta el umbral sobre el histograma.
5. En *Post-processing*, aplica suavizado y exporta como ráster o como polígonos (Esri, s. f.-d).
6. Elimina los polígonos menores a la unidad mínima de mapeo (por ejemplo 0,5 ha) con *Select By Attributes* sobre `Shape_Area`.

**Nivel 2, qué cambió (aprendizaje profundo):**

1. Digitaliza 100 a 150 polígonos por época con el **Training Samples Manager**.
2. **Export Training Data For Deep Learning**, con formato *Classified Tiles*.
3. **Train Deep Learning Model**:
   - **U-Net**, para segmentar clases en cada época;
   - **Change detector**, que usa dos imágenes de distinta fecha y entrega un ráster clasificado de cambio (Esri, s. f.-e).
4. **Classify Pixels Using Deep Learning** sobre cada época.
5. **Compute Change Raster** en modo *Categorical Difference* para obtener la matriz de transición.

## Validación

- **Create Accuracy Assessment Points** con muestreo *Stratified Random*.
- Interpreta cada punto sobre las fotos originales y calcula la matriz con **Compute Confusion Matrix**.
- El **área ajustada con IC 95 %** (Olofsson et al., 2014) no viene en la herramienta. Exporta la matriz y usa `cubo/validacion.py::olofsson`, o una hoja de cálculo con las mismas fórmulas.

## Automatizar con arcpy

El script [`arcgis/cubo_arcpy.py`](../arcgis/cubo_arcpy.py) arma el mosaico multidimensional y calcula la diferencia entre dos épocas. Se ejecuta desde la ventana de Python de ArcGIS Pro o desde un *Notebook*.

---

### Referencias

Esri. (s. f.-a). *Historical imagery ortho mapping workflow*. https://doc.arcgis.com/en/imagery/workflows/best-practices/historical-imagery-ortho-mapping-workflow.htm

Esri. (s. f.-b). *Create a multidimensional mosaic dataset from a set of time series images in ArcGIS Pro*. https://doc.esri.com/en/arcgis-pro/latest/help/data/imagery/create-a-multidimensional-mosaic-dataset-from-a-set-of-time-series-images-in-arcgis-pro.html

Esri. (s. f.-c). *Refine interior orientation using fiducials*. https://pro.arcgis.com/en/pro-app/help/data/imagery/refine-interior-orientation-using-fiducials.htm

Esri. (s. f.-d). *Pixel value change detection*. https://doc.esri.com/en/arcgis-pro/latest/help/analysis/image-analyst/pixel-value-change-detection.html

Esri. (s. f.-e). *Train Deep Learning Model (Image Analyst)*. https://pro.arcgis.com/en/pro-app/3.4/tool-reference/image-analyst/train-deep-learning-model.htm

Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment, 148*, 42–57. https://doi.org/10.1016/j.rse.2014.02.015
