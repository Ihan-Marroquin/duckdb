# Catalogo de consultas

## Vista comun (`sql/00_normalized_views.sql`)

`trips` lee los Parquet con `read_parquet(..., union_by_name=true,
filename=true)`. Normaliza `tpep_*` y `lpep_*`, agrega tipo y periodo, y conserva
el archivo para trazabilidad. `valid_trips` excluye para indicadores fechas nulas
o fuera del anio, duraciones no positivas o mayores de 24 horas, distancia
negativa y monto negativo. La vista cruda permanece disponible para auditoria.

## Ejercicio 3 - Exploracion (`sql/01_exploration.sql`)

| Consulta | Objetivo | Fuente | Resultado/decision |
|---|---|---|---|
| Archivos y filas por tipo/anio | Confirmar cobertura y volumen | `trips` | 64 archivos y 121,184,384 filas al 2026-10-06 |
| `DESCRIBE` | Identificar nombres y tipos | `trips` | Esquema comun de 25 columnas |
| Muestra aleatoria | Revisar valores reales | `trips` | Detecta codigos, nulos y rangos |
| Controles de calidad | Cuantificar inconsistencias | `trips` | Motiva separar `trips` y `valid_trips` |

Consultar Parquet directamente significa interpretar sus metadatos y columnas
durante la consulta, sin cargar antes todas las filas en una tabla. Evita
duplicar almacenamiento y permite *column pruning* y *predicate pushdown*.

## Ejercicio 4 - Preguntas analiticas (`sql/02_eda.sql`)

1. ¿Como cambia el volumen mensual por tipo?
2. ¿Que tipo registra mayor monto promedio?
3. ¿Como evolucionan distancia y duracion?
4. ¿Que diferencias existen entre amarillo y verde?
5. ¿Que proporcion se paga con tarjeta o efectivo?
6. ¿En que horas se concentra la demanda?
7. ¿Que proporcion ocurre en fin de semana?
8. ¿Como cambia la propina en pagos con tarjeta?
9. ¿Que tan alejados estan el percentil 99 y la mediana?
10. ¿Que problemas de calidad afectan cada anio y tipo?

Los resultados quedan en `docs/results/*.csv`. Los percentiles resumen valores
atipicos sin dejar que unos pocos extremos dominen el promedio.

## Ejercicios 5 y 8 - Incorporacion incremental

Las vistas usan comodines y `union_by_name`; incorporar anios no exige reescribir
el analisis. El descargador parametriza anios/tipos, valida y omite existentes.

## Ejercicio 6 - Benchmark (`sql/03_materialize.sql`)

`trips_materialized` es copia fisica de `trips`. `benchmark.py` ejecuta conteo,
resumen por tipo y agregado mensual de forma equivalente con 1, 2 y 3 anios.
Registra calentamiento, tres repeticiones, minimo, mediana y maximo.

## Ejercicio 7 - Indicadores (`sql/04_indicators.sql`)

El tablero incluye volumen, ingresos, monto, distancia, duracion, propina,
participacion de fin de semana, pagos, demanda horaria y percentiles. Cada
indicador responde una pregunta y se exporta como CSV antes de visualizarse.
