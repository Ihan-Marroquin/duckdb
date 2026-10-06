#!/usr/bin/env python3
"""Valida integridad, cobertura, esquema y conteos de los Parquet descargados."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from common import RAW, RESULTS, parquet_glob


def parquet_valido(path: Path) -> bool:
    if path.stat().st_size < 12:
        return False
    with path.open("rb") as stream:
        return stream.read(4) == b"PAR1" and (stream.seek(-4, 2) or True) and stream.read(4) == b"PAR1"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    con = duckdb.connect()

    for taxi in ("yellow", "green"):
        for year_dir in sorted((RAW / taxi).glob("20*")):
            for path in sorted(year_dir.glob("*.parquet")):
                valid = parquet_valido(path)
                rows = None
                columns = None
                if valid:
                    quoted = str(path.as_posix()).replace("'", "''")
                    rows = con.execute(
                        f"SELECT COUNT(*) FROM read_parquet('{quoted}')"
                    ).fetchone()[0]
                    columns = len(
                        con.execute(f"DESCRIBE SELECT * FROM read_parquet('{quoted}')").fetchall()
                    )
                manifest.append(
                    {
                        "taxi_type": taxi,
                        "year": int(year_dir.name),
                        "file": path.name,
                        "bytes": path.stat().st_size,
                        "valid_parquet": valid,
                        "rows": rows,
                        "columns": columns,
                    }
                )

    if not manifest:
        raise SystemExit("No hay archivos. Ejecute scripts/download_data.py primero.")

    (RESULTS / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    summary = con.execute(
        """
        SELECT regexp_extract(filename, '(yellow|green)', 1) AS taxi_type,
               regexp_extract(filename, '(\\d{4})-(\\d{2})\\.parquet$', 1)::INTEGER AS year,
               COUNT(DISTINCT filename) AS files,
               COUNT(*) AS rows
        FROM read_parquet(?, union_by_name=true, filename=true)
        GROUP BY ALL ORDER BY year, taxi_type
        """,
        [[parquet_glob("yellow"), parquet_glob("green")]],
    ).df()
    summary.to_csv(RESULTS / "file_row_counts.csv", index=False)

    invalid = [item["file"] for item in manifest if not item["valid_parquet"]]
    print(summary.to_string(index=False))
    print(f"\nArchivos: {len(manifest)} | invalidos: {len(invalid)}")
    if invalid:
        raise SystemExit("Parquet invalidos: " + ", ".join(invalid))


if __name__ == "__main__":
    main()
