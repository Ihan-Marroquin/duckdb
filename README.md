# Lab 8 - DuckDB

Laboratorio reproducible de **CC3084 - Data Science** sobre 121 millones de
viajes de NYC TLC. El proyecto descarga Parquet incrementales, consulta los
archivos directamente con DuckDB, normaliza los esquemas de taxis amarillos y
verdes, ejecuta EDA, compara Parquet contra una tabla materializada y genera un
tablero con indicadores.

**Equipo:** [Ihan-Marroquin](https://github.com/Ihan-Marroquin) y
[dpatzan2](https://github.com/dpatzan2).

Fuente: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

## Estructura y proposito

```text
data/raw/           Parquet originales por tipo/anio (ignorados por Git)
data/processed/     base DuckDB materializada (ignorada por Git)
notebooks/          recorrido interactivo del laboratorio
scripts/            descarga, validacion, analisis y benchmark reproducibles
sql/                vistas, exploracion, EDA, materializacion e indicadores
docs/               metodologia, resultados, CSV y evidencia del tablero
Dockerfile          JupyterLab con dependencias fijadas
metabase.Dockerfile Metabase con el driver DuckDB compatible
docker-compose.yml  orquestacion de JupyterLab y Metabase
```

Separar datos crudos, procesados, codigo y documentacion evita mezclar artefactos
pesados con Git y permite repetir cada etapa. Docker fija versiones y rutas, por
lo que reduce diferencias entre equipos y facilita auditar resultados.

## 1. Levantar el ambiente

Requisitos: Git, Docker Desktop con el motor iniciado, Docker Compose y al menos
10 GB libres.

```bash
git clone https://github.com/Ihan-Marroquin/duckdb.git
cd duckdb
docker compose up --build -d
docker compose ps
```

- JupyterLab: <http://localhost:8888>
- Metabase: <http://localhost:3000>

`docker compose ps` debe mostrar `lab8-lab` y `lab8-metabase` en ejecucion.
Dentro de Jupyter estan Python 3.11, DuckDB 1.5.5, pandas, PyArrow, Matplotlib y
JupyterLab. Metabase incluye el driver DuckDB 1.5.5.0.

Para detener los servicios sin borrar datos: `docker compose down`.

## 2. Descargar y validar los datos

El comando predeterminado intenta todos los meses de 2024, 2025 y 2026 para
`yellow` y `green`. Consulta la fuente oficial, conserva archivos existentes,
usa descargas temporales `.part` y valida los marcadores `PAR1`.

```bash
docker compose exec lab python scripts/download_data.py
docker compose exec lab python scripts/validate_data.py
```

Opciones utiles:

```bash
docker compose exec lab python scripts/download_data.py --years 2026
docker compose exec lab python scripts/download_data.py --years 2024 2025 --taxi green
docker compose exec lab python scripts/download_data.py --list-only
```

La completitud combina respuesta HTTP de los 72 nombres mensuales posibles,
ausencia de fallos, firma Parquet, conteo de archivos y filas con DuckDB. Al 6 de
octubre de 2026 la TLC habia publicado 12 meses de 2024, 12 de 2025 y 8 de 2026
por tipo (64 archivos). Septiembre-diciembre de 2026 aun no estaban publicados.

Los datos no se versionan: `.gitignore` excluye `data/raw/**` y
`data/processed/**`, excepto los `.gitkeep`.

## 3. Ejecutar el analisis y tablero

```bash
docker compose exec lab python scripts/run_analysis.py
```

El script consulta `data/raw/*/*/*.parquet`, exporta tablas a `docs/results/`,
escribe `docs/RESULTADOS.md` y genera `docs/dashboard.png`. La vista `trips`
conserva los datos crudos; `valid_trips` aplica reglas de calidad documentadas.

El notebook `notebooks/lab8_analysis.ipynb` permite recorrer las mismas vistas y
resultados. Las consultas se explican en `docs/CONSULTAS.md` y estan en `sql/`.

## 4. Reproducir el benchmark

```bash
docker compose exec lab python scripts/benchmark.py
```

El proceso crea `data/processed/lab8.duckdb`, materializa los 121 millones de
registros, ejecuta consultas equivalentes sobre 1, 2 y 3 anios y guarda cada
medicion en `docs/results/benchmark.csv`. El costo inicial se reporta aparte.

## 5. Consultar con Metabase

Despues del benchmark, abra Metabase y agregue una base DuckDB de solo lectura:

```text
/workspace/data/processed/lab8.duckdb
```

La tabla es `trips_materialized`. `docs/dashboard.png` conserva la evidencia del
tablero reproducible; sus CSV permiten recrear cada panel en Metabase.

## Resultados principales

- [Informe final en formato Word](docs/Informe_Laboratorio_8_DuckDB.docx)
- [Cobertura, calidad, hallazgos y tablero](docs/RESULTADOS.md)
- [Benchmark](docs/BENCHMARK.md)
- [Catalogo de consultas](docs/CONSULTAS.md)
- [Discusion final](docs/DISCUSION.md)

## Decisiones de diseno

- Rutas relativas al repositorio y consistentes con `/workspace` en Docker.
- `union_by_name=true` tolera evolucion de columnas entre meses.
- Tipo de taxi y periodo derivados del archivo para conservar trazabilidad.
- Descargas idempotentes y atomicas.
- SQL, agregados y parametros del benchmark versionados.
- Parquet y base materializada fuera de Git.
