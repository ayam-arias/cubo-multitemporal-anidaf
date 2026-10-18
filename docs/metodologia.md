# Metodología: del negativo escaneado al cambio validado

Seis fases, una sola cadena trazable. Cada fase deja un registro que permite auditar el resultado.

| Fase | Qué se hace | Producto | Control |
|---|---|---|---|
| **A · Inventario** | Guía de cobertura por vuelo, control de calidad del escaneo, conversión a COG | Lista de fotogramas por época y zona | Resolución de escaneo, rayas, saturación |
| **B · Orientación** | Marcas fiduciales, certificado de calibración de cámara, puntos de control sobre rasgos estables | Orientación interior y exterior | Residuos de los puntos de control |
| **C · Ortorrectificación** | Ortho Mapping (o equivalente) con DEM | Ortofoto por época | **RMSE con ≥ 30 puntos de chequeo independientes** |
| **D · Homogeneización** | Igualación de histograma contra la época ancla y contraste local (CLAHE) | Capas comparables en tono | Inspección visual por época |
| **E · Cubo** | Remuestreo a una grilla común y apilado en el tiempo | Ráster multidimensional (tiempo, y, x) | Misma proyección, extensión, píxel y alineación |
| **F · Cambio** | Diferencia + Otsu (dónde) y segmentación supervisada (qué) | Máscara de cambio y matriz de transición en ha | Muestreo estratificado y área ajustada con IC 95 % |

La **fase C decide el proyecto**: si dos épocas quedan desplazadas unos metros entre sí, el modelo detecta "cambio" en todos los bordes.

---

## A · Inventario

- Una época = un vuelo (misma fecha, cámara, película y escala).
- Registrar por fotograma: serie, rollo, número, fecha, escala, focal, resolución de escaneo.
- Convertir a Cloud Optimized GeoTIFF (COG) para lectura parcial y rápida.

## B · Orientación

- Usar las **marcas fiduciales** y el **certificado de calibración** de la cámara cuando exista (orientación interior rigurosa).
- Elegir una **época ancla**: la de mejor geometría, escala grande y más rasgos en común con las demás y con el presente.
- Orientar el ancla contra una referencia actual (ortofoto o imagen de alta resolución) con **15 a 20 puntos de control** sobre rasgos estables: construcciones antiguas, cruces de caminos, muelles.
- **Nunca** usar como control: línea de costa, vegetación, cauces o dunas (cambian).
- Las demás épocas se registran contra el ancla. `cubo/registro.py` propone correspondencias con SIFT + RANSAC; un fotogrametrista las revisa.

## C · Ortorrectificación y exactitud

Georreferenciar con una transformación 2D **no** corrige el relieve. El desplazamiento radial es

```
d = r · h / H        con  H = f · E
```

Ejemplo: f = 153 mm a 1:20.000 → H = 3.060 m. Un cerro de 100 m, a 10 cm del centro de la foto, se desplaza ≈ 65 m en terreno; en la esquina del formato, ≈ 106 m. Por eso se ortorrectifica con un DEM (p. ej. Copernicus GLO-30).

La exactitud **se declara**: RMSE horizontal con al menos 30 puntos de chequeo independientes de los de control (ASPRS, 2024). El RMSE de cada época viaja en los metadatos del cubo (`rmse_m`). `cubo/validacion.py::rmse` lo calcula.

## D · Homogeneización

Cada vuelo tiene otra película y otro revelado: es un **cambio de dominio**. Se reduce con

1. normalización por percentiles,
2. igualación de histograma contra la época ancla,
3. contraste local adaptativo (CLAHE).

Esto mejora la comparación de tonos; no corrige diferencias reales de contenido.

## E · Cubo: la grilla común

Un cubo exige que todas las capas compartan **sistema de referencia, extensión, tamaño de píxel y alineación**. Si no, es una pila de imágenes.

**GSD nominal = píxel de escaneo × denominador de escala.** A 1.411 dpi el píxel es de 18 µm:

| Escala | GSD |
|---|---|
| 1:20.000 | 0,36 m |
| 1:30.000 | 0,54 m |
| 1:60.000 | 1,08 m |
| 1:70.000 | 1,26 m |

**Regla:** el cubo no puede ser más fino que su época más gruesa. Remuestrear hacia arriba inventa detalle. Se agrega (promedio) hacia una grilla más gruesa; nunca al revés. Si se necesita detalle, se arma un **segundo cubo** solo con las escalas grandes.

Para combinar con satélite se usan **dos cubos** conectados por agregación:

- **cubo de detalle (≤ 1 m):** fotos aéreas + satélites submétricos;
- **cubo regional anual:** Landsat (desde 1972/1984) y Sentinel-2 (desde 2015).

`cubo/grilla.py` calcula GSD, resolución y extensión alineada; `cubo/apilar.py` construye el cubo en NetCDF.

## F · Cambio

**Nivel 1 – dónde cambió (no supervisado, garantizado):** diferencia absoluta entre épocas homogeneizadas, umbral automático de Otsu y unidad mínima de mapeo (p. ej. 0,5 ha). No requiere etiquetas. Ver `cubo/cambio.py`.

**Nivel 2 – qué cambió (supervisado):**

- U-Net con codificador preentrenado para segmentar clases por época; redes siamesas para cambio directo;
- 100 a 150 polígonos etiquetados por época;
- clases sugeridas: industrial, edificación, vegetación, arena y duna, agua y humedal;
- desempeño reportado **por época** (cambio de dominio);
- SAM ayuda a delinear objetos, pero no asigna clase.

Resultado: **matriz de transición en hectáreas**.

## Validación

- Muestreo aleatorio **estratificado** por clase mapeada, interpretado sobre las fotos originales.
- Exactitud global, de usuario y de productor; **área ajustada con IC 95 %** (Olofsson et al., 2014). Ver `cubo/validacion.py::olofsson`, probado con el ejemplo publicado.
- Kappa no se usa como métrica principal (Pontius & Millones, 2011; Foody, 2020).

## Límites

1. **Inferencia no es evidencia.** La superresolución y la colorización inventan detalle plausible: sirven para comunicar, nunca para medir.
2. **La exactitud se declara.** Todo producto arrastra el error de la orientación.
3. **El modelo hereda el sesgo** de quien etiquetó. Lo que el modelo propone, el fotogrametrista lo verifica.
4. Es un cubo **fotográfico y pancromático**, no ARD en el sentido del CEOS: su aporte es temporal, no espectral.
