"""Transformación de datos crudos (data/raw) → datos limpios (data/processed).

Une los CSV de Bike Sharing (day/hour) con fuentes de clima externas y
genera datasets limpios listos para carga.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

INPUT_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/processed")
COLUMNA_FECHA = "dteday"
COLUMNAS_REQUERIDAS = ["dteday", "cnt"]

log = logging.getLogger(__name__)


class TransformError(RuntimeError):
    """Error recuperable durante la transformación."""


def cargar_crudos(input_dir: Path) -> dict[str, pd.DataFrame]:
    log.info(f"Cargando CSVs desde {input_dir}/...")
    dataframes: dict[str, pd.DataFrame] = {}
    for nombre in ["day.csv", "hour.csv"]:
        ruta = input_dir / nombre
        if not ruta.exists():
            log.warning(f"  ⚠ {ruta} no existe, se omite.")
            continue
        df = pd.read_csv(ruta)
        dataframes[nombre] = df
        log.info(f"  ✓ {nombre}: {df.shape[0]} filas × {df.shape[1]} columnas")
    return dataframes


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Limpiando dataset...")
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise TransformError(
            f"Columnas requeridas ausentes: {faltantes}. "
            f"Disponibles: {list(df.columns)}"
        )

    antes = len(df)
    df = df.dropna(subset=COLUMNAS_REQUERIDAS).copy()
    if len(df) < antes:
        log.warning(f"  ⚠ Filas descartadas por nulos: {antes - len(df)}")

    df[COLUMNA_FECHA] = pd.to_datetime(df[COLUMNA_FECHA], errors="coerce")
    df = df.dropna(subset=[COLUMNA_FECHA])

    log.info(f"  ✓ Filas tras limpieza: {len(df)}")
    return df


def guardar_procesado(nombre: str, df: pd.DataFrame, formato: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(nombre).stem
    if formato == "parquet":
        ruta = OUTPUT_DIR / f"{stem}.parquet"
        df.to_parquet(ruta, index=False)
    else:
        ruta = OUTPUT_DIR / f"{stem}.csv"
        df.to_csv(ruta, index=False)
    log.info(f"  ✓ Guardado procesado: {ruta}")
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Limpia y normaliza los datos crudos de data/raw/ "
            "y los guarda en data/processed/."
        )
    )
    parser.add_argument(
        "--formato",
        choices=["csv", "parquet"],
        default="csv",
        help="Formato de salida (default: csv)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("=" * 55)
    log.info("  TRANSFORMACIÓN — Bike Sharing + Clima")
    log.info("=" * 55)

    try:
        dataframes = cargar_crudos(INPUT_DIR)
        if not dataframes:
            raise TransformError(
                "No hay datos crudos en data/raw/. Ejecuta extract.py primero."
            )

        for nombre, df in dataframes.items():
            limpio = limpiar(df)
            guardar_procesado(nombre, limpio, args.formato)
    except TransformError as e:
        log.error(f"Transformación abortada: {e}")
        return 1

    log.info("=" * 55)
    log.info("  Transformación completada exitosamente ✓")
    log.info("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
