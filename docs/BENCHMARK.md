# Benchmark: Parquet directo vs tabla DuckDB

La tabla materializada contiene **121,184,384 filas** y se creo en **275.44 s**.
Cada medicion tiene un calentamiento y tres repeticiones; se reporta la mediana.

| Años | Consulta | Parquet (s) | Tabla (s) | Aceleracion tabla |
|---|---:|---:|---:|---:|
| 2024 | count | 0.0264 | 0.0124 | 2.12x |
| 2024 | monthly | 0.3324 | 0.4330 | 0.77x |
| 2024 | summary | 0.3879 | 0.2712 | 1.43x |
| 2024+2025 | count | 0.0555 | 0.0222 | 2.50x |
| 2024+2025 | monthly | 0.6001 | 0.7669 | 0.78x |
| 2024+2025 | summary | 0.7939 | 0.5674 | 1.40x |
| 2024+2025+2026 | count | 0.0550 | 0.0306 | 1.80x |
| 2024+2025+2026 | monthly | 0.9323 | 1.2690 | 0.73x |
| 2024+2025+2026 | summary | 1.2201 | 0.8891 | 1.37x |

## Interpretacion

Parquet directo evita el costo y el espacio de una carga inicial, conserva portabilidad y se beneficia del column pruning y predicate pushdown. Es apropiado para exploracion y datos que se agregan por archivos.

La tabla materializada paga un costo inicial, pero puede reducir el overhead de abrir y combinar muchos archivos en consultas repetidas. Conviene para tableros de alta frecuencia o transformaciones estables. Los resultados dependen del cache del sistema, hardware y selectividad; por eso el CSV conserva minimo, mediana y maximo.
