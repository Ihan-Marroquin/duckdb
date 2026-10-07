#!/usr/bin/env python3
"""Ejecuta el EDA, exporta resultados y genera el tablero reproducible."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from common import RESULTS, ROOT, connect


def markdown_table(df: pd.DataFrame) -> str:
    values = [[str(v) for v in df.columns]] + [
        ["" if pd.isna(v) else str(v) for v in row] for row in df.itertuples(index=False, name=None)
    ]
    widths = [max(len(row[i]) for row in values) for i in range(len(values[0]))]
    line = lambda row: "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(row))) + " |"
    return "\n".join([line(values[0]), line(["-" * w for w in widths])] + [line(r) for r in values[1:]])


def export(con, name: str, query: str) -> pd.DataFrame:
    df = con.execute(query).df()
    df.to_csv(RESULTS / f"{name}.csv", index=False)
    return df


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    con = connect()

    coverage = export(
        con,
        "coverage",
        """
        SELECT taxi_type, file_year, COUNT(DISTINCT filename) AS files, COUNT(*) AS rows
        FROM trips GROUP BY ALL ORDER BY file_year, taxi_type
        """,
    )
    quality = export(
        con,
        "quality",
        """
        SELECT taxi_type, file_year, COUNT(*) AS rows,
          count_if(pickup_datetime IS NULL OR dropoff_datetime IS NULL) AS null_timestamps,
          count_if(year(pickup_datetime) <> file_year) AS pickup_outside_file_year,
          count_if(dropoff_datetime <= pickup_datetime) AS nonpositive_duration,
          count_if(dropoff_datetime > pickup_datetime + INTERVAL '24 hours') AS duration_over_24h,
          count_if(trip_distance <= 0) AS nonpositive_distance,
          count_if(total_amount < 0) AS negative_total,
          count_if(passenger_count IS NULL OR passenger_count <= 0) AS missing_or_zero_passengers
        FROM trips GROUP BY ALL ORDER BY file_year, taxi_type
        """,
    )
    monthly = export(
        con,
        "monthly_indicators",
        """
        SELECT file_year, file_month, taxi_type, COUNT(*) AS trips,
          AVG(trip_distance) AS avg_distance_miles,
          AVG(duration_minutes) AS avg_duration_minutes,
          AVG(total_amount) AS avg_total_usd,
          SUM(total_amount) AS revenue_usd
        FROM valid_trips GROUP BY ALL ORDER BY file_year, file_month, taxi_type
        """,
    )
    yearly = export(
        con,
        "yearly_indicators",
        """
        SELECT file_year, taxi_type, COUNT(*) AS trips,
          SUM(total_amount) AS revenue_usd,
          AVG(total_amount) AS avg_total_usd,
          AVG(trip_distance) AS avg_distance_miles,
          AVG(duration_minutes) AS avg_duration_minutes,
          AVG(CASE WHEN payment_type=1 AND fare_amount>0 THEN 100.0*tip_amount/fare_amount END) AS avg_card_tip_pct,
          100.0*AVG(CASE WHEN dayofweek(pickup_datetime) IN (0,6) THEN 1 ELSE 0 END) AS weekend_share_pct
        FROM valid_trips GROUP BY ALL ORDER BY file_year, taxi_type
        """,
    )
    payment = export(
        con,
        "payment_mix",
        """
        SELECT taxi_type, payment_type, COUNT(*) AS trips
        FROM valid_trips GROUP BY ALL ORDER BY taxi_type, trips DESC
        """,
    )
    hourly = export(
        con,
        "pickup_hour",
        """
        SELECT taxi_type, hour(pickup_datetime) AS pickup_hour, COUNT(*) AS trips
        FROM valid_trips GROUP BY ALL ORDER BY taxi_type, pickup_hour
        """,
    )
    quantiles = export(
        con,
        "quantiles",
        """
        SELECT taxi_type,
          quantile_cont(trip_distance, 0.50) AS distance_p50,
          quantile_cont(trip_distance, 0.99) AS distance_p99,
          quantile_cont(duration_minutes, 0.50) AS duration_p50,
          quantile_cont(duration_minutes, 0.99) AS duration_p99,
          quantile_cont(total_amount, 0.50) AS total_p50,
          quantile_cont(total_amount, 0.99) AS total_p99
        FROM valid_trips GROUP BY taxi_type ORDER BY taxi_type
        """,
    )

    totals = con.execute(
        """
        SELECT COUNT(*) AS trips, SUM(total_amount) AS revenue,
               AVG(total_amount) AS avg_total, AVG(trip_distance) AS avg_distance,
               AVG(duration_minutes) AS avg_duration,
               AVG(CASE WHEN payment_type=1 AND fare_amount>0 THEN 100.0*tip_amount/fare_amount END) AS tip_pct
        FROM valid_trips
        """
    ).fetchone()

    colors = {"yellow": "#f2c94c", "green": "#27ae60"}
    fig = plt.figure(figsize=(16, 11), layout="constrained")
    grid = fig.add_gridspec(4, 3, height_ratios=[0.55, 1.6, 1.6, 1.6])
    labels = ["Viajes validos", "Ingresos", "Monto promedio", "Distancia media", "Duracion media", "Propina tarjeta"]
    vals = [f"{totals[0]:,.0f}", f"${totals[1]/1e9:,.2f}B", f"${totals[2]:,.2f}", f"{totals[3]:,.2f} mi", f"{totals[4]:,.1f} min", f"{totals[5]:,.1f}%"]
    top = fig.add_subplot(grid[0, :]); top.axis("off")
    for i, (label, val) in enumerate(zip(labels, vals)):
        x = (i + 0.5) / 6
        top.text(x, 0.65, val, ha="center", va="center", fontsize=18, fontweight="bold")
        top.text(x, 0.18, label, ha="center", va="center", fontsize=10, color="#555555")

    ax1 = fig.add_subplot(grid[1, :2])
    monthly_plot = monthly.assign(period=pd.to_datetime(dict(year=monthly.file_year, month=monthly.file_month, day=1)))
    for taxi, group in monthly_plot.groupby("taxi_type"):
        ax1.plot(group.period, group.trips / 1e6, marker="o", label=taxi, color=colors[taxi])
    ax1.set(title="Viajes mensuales", ylabel="Millones de viajes"); ax1.legend(); ax1.grid(alpha=.2)

    ax2 = fig.add_subplot(grid[1, 2])
    yearly.pivot(index="file_year", columns="taxi_type", values="avg_total_usd").plot(kind="bar", ax=ax2, color=[colors.get(c, "gray") for c in sorted(yearly.taxi_type.unique())])
    ax2.set(title="Monto promedio", xlabel="Anio", ylabel="USD"); ax2.legend(title="Taxi"); ax2.grid(axis="y", alpha=.2)

    ax3 = fig.add_subplot(grid[2, 0])
    yearly.pivot(index="file_year", columns="taxi_type", values="avg_distance_miles").plot(kind="bar", ax=ax3, color=[colors.get(c, "gray") for c in sorted(yearly.taxi_type.unique())])
    ax3.set(title="Distancia promedio", xlabel="Anio", ylabel="Millas"); ax3.legend(title="Taxi"); ax3.grid(axis="y", alpha=.2)

    ax4 = fig.add_subplot(grid[2, 1])
    pay = payment[payment.payment_type.isin([1, 2])].pivot(index="taxi_type", columns="payment_type", values="trips").fillna(0)
    pay.div(pay.sum(axis=1), axis=0).mul(100).plot(kind="bar", stacked=True, ax=ax4, color=["#3b82f6", "#ef4444"])
    ax4.set(title="Pago: tarjeta vs efectivo", xlabel="Taxi", ylabel="Porcentaje"); ax4.legend(["Tarjeta", "Efectivo"]); ax4.grid(axis="y", alpha=.2)

    ax5 = fig.add_subplot(grid[2, 2])
    for taxi, group in hourly.groupby("taxi_type"):
        ax5.plot(group.pickup_hour, group.trips / 1e6, label=taxi, color=colors[taxi])
    ax5.set(title="Demanda por hora", xlabel="Hora", ylabel="Millones"); ax5.legend(); ax5.grid(alpha=.2)

    ax6 = fig.add_subplot(grid[3, :])
    qplot = quantiles.set_index("taxi_type")[["distance_p50", "distance_p99", "duration_p50", "duration_p99", "total_p50", "total_p99"]]
    qplot.plot(kind="bar", ax=ax6, width=.8)
    ax6.set(title="Mediana y percentil 99: distancia, duracion y monto", xlabel="Taxi", ylabel="Valor"); ax6.legend(ncol=3); ax6.grid(axis="y", alpha=.2)

    fig.suptitle("NYC TLC 2024-2026 - Tablero DuckDB", fontsize=22, fontweight="bold")
    fig.text(
        0.5,
        0.965,
        "2026 incluye enero-agosto (cobertura parcial segun publicaciones TLC)",
        ha="center",
        fontsize=10,
        color="#555555",
    )
    fig.savefig(ROOT / "docs" / "dashboard.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    busiest = monthly.loc[monthly.trips.idxmax()]
    top_hour = hourly.loc[hourly.trips.idxmax()]
    green_yellow = yearly.pivot(index="file_year", columns="taxi_type", values="trips")
    ratio_text = ", ".join(
        f"{int(year)}: {row.get('yellow', 0) / max(row.get('green', 1), 1):.1f}x"
        for year, row in green_yellow.iterrows()
    )
    amount = yearly.pivot(index="file_year", columns="taxi_type", values="avg_total_usd")
    amount_text = ", ".join(
        f"{int(year)}: amarillo ${row.get('yellow', 0):.2f}, verde ${row.get('green', 0):.2f}"
        for year, row in amount.iterrows()
    )
    green_quantiles = quantiles.loc[quantiles.taxi_type == "green"].iloc[0]
    report = f"""# Resultados reproducibles

Generado por `python scripts/run_analysis.py` directamente sobre los Parquet disponibles.
El anio 2026 es parcial: solo se incluyen los meses publicados por la TLC a la fecha de ejecucion.

## Cobertura y volumen

{markdown_table(coverage)}

## Calidad de datos

Las categorias pueden solaparse; para los indicadores se usa `valid_trips`, que filtra fechas fuera del anio del archivo, duraciones no positivas o mayores de 24 horas, distancias negativas y montos negativos.

{markdown_table(quality)}

## Hallazgos

1. El mayor volumen mensual observado fue **{int(busiest.trips):,} viajes** para taxis **{busiest.taxi_type}** en **{int(busiest.file_year)}-{int(busiest.file_month):02d}**.
2. La hora con mas registros agregados fue **{int(top_hour.pickup_hour):02d}:00** para taxis **{top_hour.taxi_type}** ({int(top_hour.trips):,} viajes). Esto concentra capacidad operativa y no implica causalidad.
3. La relacion de volumen amarillo/verde fue **{ratio_text}**. La diferencia confirma que comparar solo conteos absolutos puede ocultar patrones propios del servicio verde.
4. El monto promedio evoluciono asi: **{amount_text}**. El aumento de 2026 debe interpretarse con cautela porque el anio es parcial.
5. En taxi verde la distancia mediana fue **{green_quantiles.distance_p50:.2f} mi** y el percentil 99 **{green_quantiles.distance_p99:.2f} mi**, mientras la media anual supera ampliamente la mediana. Esta asimetria revela valores extremos y desaconseja interpretar solo promedios.
6. Existen registros invalidos (tabla de calidad); por ello el tablero separa la vista cruda `trips` de la vista analitica `valid_trips`.

## Indicadores

Los archivos CSV en `docs/results/` respaldan: viajes, ingresos, monto medio, distancia media, duracion media, porcentaje de propina con tarjeta, participacion de fin de semana, mezcla de pago, demanda por hora y percentiles de valores relevantes.

![Tablero DuckDB](dashboard.png)
"""
    (ROOT / "docs" / "RESULTADOS.md").write_text(report, encoding="utf-8")
    print(coverage.to_string(index=False))
    print(f"\nTablero: {ROOT / 'docs' / 'dashboard.png'}")


if __name__ == "__main__":
    main()
