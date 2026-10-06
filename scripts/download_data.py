#!/usr/bin/env python3
"""Descarga incremental de NYC TLC Trip Record Data en formato Parquet.

Por defecto obtiene los archivos publicados de taxis amarillos y verdes para
2024, 2025 y 2026. Los archivos se guardan en
``data/raw/<tipo>/<anio>/`` y nunca se vuelven a descargar si ya existe un
Parquet valido. Una descarga incompleta usa el sufijo ``.part``.

Ejemplos:
    python scripts/download_data.py
    python scripts/download_data.py --years 2026 --taxi yellow
    python scripts/download_data.py --years 2024 2025 --workers 4
    python scripts/download_data.py --list-only
"""

from __future__ import annotations

import argparse
import concurrent.futures
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

import requests

ANIOS = (2024, 2025, 2026)
TIPOS_TAXI = ("yellow", "green")
URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
DIR_DESTINO = Path("data/raw")
TIEMPO_ESPERA = 90
INTENTOS = 3
BLOQUE = 1024 * 1024
SUFIJO_TEMPORAL = ".part"
MAGIA_PARQUET = b"PAR1"

_impresion = threading.Lock()


@dataclass(frozen=True)
class ArchivoTLC:
    tipo: str
    anio: int
    mes: int

    @property
    def nombre(self) -> str:
        return f"{self.tipo}_tripdata_{self.anio}-{self.mes:02d}.parquet"

    @property
    def url(self) -> str:
        return f"{URL_BASE}/{self.nombre}"

    @property
    def destino(self) -> Path:
        return DIR_DESTINO / self.tipo / str(self.anio) / self.nombre

    @property
    def etiqueta(self) -> str:
        return f"{self.tipo} {self.anio}-{self.mes:02d}"


def imprimir(mensaje: str) -> None:
    with _impresion:
        print(mensaje, flush=True)


def formato_tamanio(n: float) -> str:
    for unidad in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unidad == "GiB":
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GiB"


def parquet_valido(ruta: Path) -> bool:
    """Comprueba tamano y marcadores PAR1 al inicio y al final del archivo."""
    if not ruta.is_file() or ruta.stat().st_size < 12:
        return False
    try:
        with ruta.open("rb") as archivo:
            inicio = archivo.read(4)
            archivo.seek(-4, 2)
            final = archivo.read(4)
    except OSError:
        return False
    return inicio == MAGIA_PARQUET and final == MAGIA_PARQUET


def esta_publicado(archivo: ArchivoTLC) -> bool:
    try:
        respuesta = requests.head(
            archivo.url, timeout=TIEMPO_ESPERA, allow_redirects=True
        )
        return respuesta.ok
    except requests.RequestException:
        return False


def descargar_archivo(archivo: ArchivoTLC) -> tuple[str, str, int]:
    """Devuelve (estado, etiqueta, bytes) para un archivo mensual."""
    destino = archivo.destino
    destino.parent.mkdir(parents=True, exist_ok=True)

    if parquet_valido(destino):
        imprimir(f"[omite] {archivo.etiqueta}: ya existe")
        return "omitido", archivo.etiqueta, destino.stat().st_size

    if destino.exists():
        destino.unlink()

    if not esta_publicado(archivo):
        imprimir(f"[falta] {archivo.etiqueta}: no publicado")
        return "no_publicado", archivo.etiqueta, 0

    temporal = destino.with_name(destino.name + SUFIJO_TEMPORAL)
    ultimo_error: Exception | None = None

    for intento in range(1, INTENTOS + 1):
        try:
            escritos = 0
            with requests.get(
                archivo.url, stream=True, timeout=TIEMPO_ESPERA
            ) as respuesta:
                respuesta.raise_for_status()
                with temporal.open("wb") as salida:
                    for bloque in respuesta.iter_content(chunk_size=BLOQUE):
                        if bloque:
                            salida.write(bloque)
                            escritos += len(bloque)

            if escritos == 0 or not parquet_valido(temporal):
                raise requests.RequestException("archivo vacio o Parquet invalido")

            temporal.replace(destino)
            imprimir(f"[listo] {archivo.etiqueta}: {formato_tamanio(escritos)}")
            return "descargado", archivo.etiqueta, escritos
        except (OSError, requests.RequestException) as error:
            ultimo_error = error
            temporal.unlink(missing_ok=True)
            imprimir(f"[reintento {intento}/{INTENTOS}] {archivo.etiqueta}: {error}")

    imprimir(f"[ERROR] {archivo.etiqueta}: {ultimo_error}")
    return "fallido", archivo.etiqueta, 0


def construir_plan(tipos: tuple[str, ...], anios: tuple[int, ...]) -> list[ArchivoTLC]:
    return [
        ArchivoTLC(tipo, anio, mes)
        for anio in anios
        for tipo in tipos
        for mes in range(1, 13)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga incremental de Parquet de taxis NYC TLC (2024-2026)."
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        choices=ANIOS,
        default=list(ANIOS),
        metavar="ANIO",
        help="anios a descargar (por defecto: 2024 2025 2026)",
    )
    parser.add_argument(
        "--taxi",
        choices=(*TIPOS_TAXI, "all"),
        default="all",
        help="tipo de taxi (por defecto: all)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        choices=range(1, 9),
        metavar="N",
        help="descargas simultaneas, entre 1 y 8 (por defecto: 4)",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="muestra el plan sin consultar ni descargar",
    )
    args = parser.parse_args()

    tipos = TIPOS_TAXI if args.taxi == "all" else (args.taxi,)
    anios = tuple(sorted(set(args.years)))
    plan = construir_plan(tipos, anios)

    if args.list_only:
        for archivo in plan:
            print(f"{archivo.etiqueta}\t{archivo.url}\t{archivo.destino}")
        return 0

    print(
        f"Plan: {len(plan)} archivos posibles | anios={anios} | "
        f"tipos={tipos} | workers={args.workers}"
    )
    resultados: list[tuple[str, str, int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ejecutor:
        futuros = [ejecutor.submit(descargar_archivo, archivo) for archivo in plan]
        for futuro in concurrent.futures.as_completed(futuros):
            resultados.append(futuro.result())

    estados = ("descargado", "omitido", "no_publicado", "fallido")
    conteos = {estado: sum(r[0] == estado for r in resultados) for estado in estados}
    bytes_totales = sum(r[2] for r in resultados if r[0] == "descargado")

    print("\nRESUMEN")
    for estado in estados:
        print(f"  {estado:13}: {conteos[estado]}")
    print(f"  bytes nuevos : {formato_tamanio(bytes_totales)}")

    faltantes = [r[1] for r in resultados if r[0] == "no_publicado"]
    if faltantes:
        print("  no publicados: " + ", ".join(sorted(faltantes)))
    return 1 if conteos["fallido"] else 0


if __name__ == "__main__":
    sys.exit(main())
