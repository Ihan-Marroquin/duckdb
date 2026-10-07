#!/usr/bin/env python3
"""Compara Parquet directo contra una tabla materializada de DuckDB."""

from __future__ import annotations

import statistics
import time

import duckdb
import pandas as pd

from common import PROCESSED, RESULTS, ROOT, connect, create_scoped_view

DB_PATH = PROCESSED / "lab8.duckdb"
REPETITIONS = 3
SCOPES = [(2024,), (2024, 2025), (2024, 2025, 2026)]
QUERIES = {
    "count": "SELECT COUNT(*) FROM {source}",
    "summary": """
        SELECT taxi_type, COUNT(*), AVG(trip_distance), AVG(total_amount)
        FROM {source} GROUP BY taxi_type
    """,
    "monthly": """
        SELECT file_year, file_month, taxi_type, COUNT(*), SUM(total_amount)
        FROM {source} GROUP BY ALL ORDER BY ALL
    """,
}


def timed(con: duckdb.DuckDBPyConnection, sql: str) -> float:
    start = time.perf_counter()
    con.execute(sql).fetchall()
    return time.perf_counter() - start


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    con = connect(str(DB_PATH), threads=4)
    start = time.perf_counter()
    con.execute((ROOT / "sql" / "03_materialize.sql").read_text(encoding="utf-8"))
    materialization_seconds = time.perf_counter() - start
    materialized_rows = con.execute("SELECT COUNT(*) FROM trips_materialized").fetchone()[0]

    records: list[dict] = []
    for years in SCOPES:
        create_scoped_view(con, years, "trips_direct")
        years_sql = ",".join(str(y) for y in years)
        sources = {
            "parquet": "trips_direct",
            "duckdb_table": f"(SELECT * FROM trips_materialized WHERE file_year IN ({years_sql}))",
        }
        for query_name, template in QUERIES.items():
            for strategy, source in sources.items():
                sql = template.format(source=source)
                timed(con, sql)  # calentamiento
                samples = [timed(con, sql) for _ in range(REPETITIONS)]
                records.append(
                    {
                        "years": "+".join(map(str, years)),
                        "year_count": len(years),
                        "query": query_name,
                        "strategy": strategy,
                        "median_seconds": statistics.median(samples),
                        "min_seconds": min(samples),
                        "max_seconds": max(samples),
                        "repetitions": REPETITIONS,
                    }
                )

    df = pd.DataFrame(records)
    df.to_csv(RESULTS / "benchmark.csv", index=False)
    pivot = df.pivot_table(
        index=["years", "query"], columns="strategy", values="median_seconds"
    ).reset_index()
    pivot["table_speedup"] = pivot["parquet"] / pivot["duckdb_table"]
    pivot.to_csv(RESULTS / "benchmark_comparison.csv", index=False)

    lines = [
        "# Benchmark: Parquet directo vs tabla DuckDB",
        "",
        f"La tabla materializada contiene **{materialized_rows:,} filas** y se creo en **{materialization_seconds:.2f} s**.",
        "Cada medicion tiene un calentamiento y tres repeticiones; se reporta la mediana.",
        "",
        "| Años | Consulta | Parquet (s) | Tabla (s) | Aceleracion tabla |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in pivot.itertuples(index=False):
        lines.append(
            f"| {row.years} | {row.query} | {row.parquet:.4f} | "
            f"{row.duckdb_table:.4f} | {row.table_speedup:.2f}x |"
        )
    lines += [
        "",
        "## Interpretacion",
        "",
        "Parquet directo evita el costo y el espacio de una carga inicial, conserva portabilidad y se beneficia del column pruning y predicate pushdown. Es apropiado para exploracion y datos que se agregan por archivos.",
        "",
        "La tabla materializada paga un costo inicial, pero puede reducir el overhead de abrir y combinar muchos archivos en consultas repetidas. Conviene para tableros de alta frecuencia o transformaciones estables. Los resultados dependen del cache del sistema, hardware y selectividad; por eso el CSV conserva minimo, mediana y maximo.",
    ]
    (ROOT / "docs" / "BENCHMARK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:7]))
    print(f"Resultados: {RESULTS / 'benchmark.csv'}")


if __name__ == "__main__":
    main()
