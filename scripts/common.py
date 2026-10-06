"""Utilidades compartidas por el analisis, tablero y benchmark."""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "docs" / "results"
VIEWS_SQL = ROOT / "sql" / "00_normalized_views.sql"


def parquet_glob(tipo: str, years: tuple[int, ...] | None = None) -> str:
    if years is None:
        patron = RAW / tipo / "*" / "*.parquet"
        return patron.as_posix()
    archivos: list[str] = []
    for year in years:
        archivos.extend(str(p.as_posix()) for p in sorted((RAW / tipo / str(year)).glob("*.parquet")))
    if not archivos:
        raise FileNotFoundError(f"No hay Parquet de {tipo} para {years}")
    return "[" + ",".join(repr(path) for path in archivos) + "]"


def ensure_data() -> None:
    for tipo in ("yellow", "green"):
        if not any((RAW / tipo).glob("*/*.parquet")):
            raise FileNotFoundError(
                f"No se encontraron datos {tipo}. Ejecute scripts/download_data.py."
            )


def connect(database: str = ":memory:", threads: int = 4) -> duckdb.DuckDBPyConnection:
    ensure_data()
    con = duckdb.connect(database)
    con.execute(f"SET threads={threads}")
    con.execute("SET preserve_insertion_order=false")
    con.execute(VIEWS_SQL.read_text(encoding="utf-8"))
    return con


def create_scoped_view(
    con: duckdb.DuckDBPyConnection,
    years: tuple[int, ...],
    name: str = "trips_scope",
) -> None:
    yellow = parquet_glob("yellow", years)
    green = parquet_glob("green", years)
    template = VIEWS_SQL.read_text(encoding="utf-8").split(
        "CREATE OR REPLACE VIEW valid_trips"
    )[0]
    template = template.replace("'data/raw/yellow/*/*.parquet'", yellow)
    template = template.replace("'data/raw/green/*/*.parquet'", green)
    template = template.replace("CREATE OR REPLACE VIEW trips", f"CREATE OR REPLACE VIEW {name}")
    con.execute(template)
