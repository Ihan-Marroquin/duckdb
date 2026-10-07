# Discusion final

## 9.1 Caracteristicas utiles de DuckDB

Leer varios Parquet con comodin, unificar esquemas por nombre, obtener el archivo
de origen, ejecutar SQL vectorizado y materializar sin servidor. La misma
consulta escala de un mes a varios anios cambiando solo los archivos.

## 9.2 Parquet directo

Ventajas: no requiere carga previa, conserva portabilidad, evita copias y lee
solo columnas/grupos relevantes. Limitaciones: muchos archivos agregan overhead;
cambios incompatibles requieren normalizacion; consultas repetidas vuelven a
pagar parte de la lectura.

## 9.3 Tabla materializada

Ventajas: esquema estable y menor overhead para consultas repetidas o tableros.
Limitaciones: tiempo/espacio de carga, refresco al llegar datos y un solo proceso
con permiso de escritura por archivo DuckDB.

## 9.4 Comparacion con Pandas

DuckDB filtra y agrega sin convertir 121 millones de filas en un DataFrame. Esto
reduce memoria y aprovecha Parquet. Pandas se usa despues para agregados pequenos
y visualizacion.

## 9.5 Incorporar datos con cambios minimos

Particionamiento `tipo/anio`, comodines, `union_by_name`, vista normalizada y
descargador parametrico desacoplan adquisicion y analisis.

## 9.6 Automatizacion en produccion

Se programarian deteccion, descarga, validacion de firma/esquema/conteos,
refresco transaccional, pruebas de calidad, tablero y alertas.

## 9.7 Decisiones para reproducibilidad

Versiones fijadas, rutas relativas, SQL versionado, descargas atomicas e
idempotentes, datos fuera de Git, agregados auditables y benchmark explicito.

## 9.8 Aprendizaje con gran volumen

Con 121 millones de registros, particionamiento, metadatos, filtros tempranos y
separacion entre datos crudos y validos son decisiones centrales. Duplicar datos,
inferir esquemas o leer columnas innecesarias tiene un costo visible.
