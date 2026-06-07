"""Extracción del Bike Sharing Dataset (UCI).

Descarga el dataset desde UCI ML Repository usando ucimlrepo,
lo procesa, lo guarda localmente y, si GCS_BUCKET_NAME está configurado,
lo sube a GCS.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os
from ucimlrepo import fetch_ucirepo

DATASET_ID = 275
CSV_FILES = ["day.csv", "hour.csv"]
MIN_FILAS = 100
MIN_COLUMNAS = 5
OUTPUT_DIR = Path("data/raw")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")

log = logging.getLogger(__name__)


class ExtractError(RuntimeError):
    """Error recuperable durante la extracción."""


# 1. OBTENCIÓN Y PROCESAMIENTO DESDE UCI


def obtener_dataframes_uci() -> dict[str, pd.DataFrame]:
    log.info(f"Obteniendo dataset desde UCI ML Repository (ID {DATASET_ID})...")
    try:
        bike_sharing = fetch_ucirepo(id=DATASET_ID)
    except Exception as e:
        raise ExtractError(f"Error al obtener dataset vía ucimlrepo: {e}") from e

    df_hour = bike_sharing.data.original
    if df_hour is None or df_hour.empty:
        raise ExtractError("El dataset obtenido de ucimlrepo está vacío o no contiene la estructura original esperada.")

    log.info(f"  ✓ Datos horarios (hour.csv) obtenidos: {df_hour.shape[0]} filas × {df_hour.shape[1]} columnas")

    log.info("Reconstruyendo datos diarios (day.csv) a partir de los datos horarios...")
    try:
        grouped = df_hour.groupby('dteday')
        
        def round_half_up(series):
            return int(series.mean() + 0.5)

        agg_dict = {
            'season': 'first',
            'yr': 'first',
            'mnth': 'first',
            'holiday': 'first',
            'weekday': 'first',
            'workingday': 'first',
            'weathersit': round_half_up,
            'temp': lambda x: round(x.mean(), 6),
            'atemp': lambda x: round(x.mean(), 6),
            'hum': lambda x: round(x.mean(), 6),
            'windspeed': lambda x: round(x.mean(), 6),
            'casual': 'sum',
            'registered': 'sum',
            'cnt': 'sum'
        }
        
        df_day = grouped.agg(agg_dict).reset_index()
        df_day.insert(0, 'instant', range(1, len(df_day) + 1))
        
        log.info(f"  ✓ Datos diarios (day.csv) reconstruidos: {df_day.shape[0]} filas × {df_day.shape[1]} columnas")
    except Exception as e:
        raise ExtractError(f"Error al reconstruir el dataset diario: {e}") from e

    return {
        "day.csv": df_day,
        "hour.csv": df_hour
    }


# 3. VALIDACIÓN


def validar_dataset(nombre: str, df: pd.DataFrame) -> None:
    log.info(f"Validando {nombre}...")
    errores: list[str] = []

    if df.shape[0] < MIN_FILAS:
        errores.append(
            f"  ✗ Filas: {df.shape[0]} (mínimo requerido: {MIN_FILAS})"
        )
    else:
        log.info(f"  ✓ Filas    : {df.shape[0]} >= {MIN_FILAS}")

    if df.shape[1] < MIN_COLUMNAS:
        errores.append(
            f"  ✗ Columnas: {df.shape[1]} (mínimo requerido: {MIN_COLUMNAS})"
        )
    else:
        log.info(f"  ✓ Columnas : {df.shape[1]} >= {MIN_COLUMNAS}")

    nulos = int(df.isnull().sum().sum())
    if nulos > 0:
        log.warning(
            f"  ⚠ Valores nulos detectados: {nulos} — "
            "revisar antes de transformar"
        )
    else:
        log.info("  ✓ Sin valores nulos")

    if errores:
        for err in errores:
            log.error(err)
        raise ExtractError(f"Validación fallida para {nombre}")

    log.info(f"  ✓ {nombre} validado correctamente")


# 4. GUARDADO LOCAL


def guardar_local(nombre: str, df: pd.DataFrame, formato: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(nombre).stem

    if formato == "parquet":
        ruta = OUTPUT_DIR / f"{stem}.parquet"
        df.to_parquet(ruta, index=False)
    else:
        ruta = OUTPUT_DIR / f"{stem}.csv"
        df.to_csv(ruta, index=False)

    log.info(f"  ✓ Guardado local: {ruta}")
    return ruta


# 5. SUBIDA A GCS (opcional)


def upload_to_gcs(ruta_local: Path, bucket_name: str) -> None:
    try:
        from google.cloud import storage
    except ImportError as e:
        raise ExtractError(
            "Falta la dependencia google-cloud-storage. "
            "Instálala con: pip install google-cloud-storage"
        ) from e

    destino = f"raw/{ruta_local.name}"
    log.info(f"Subiendo a GCS: gs://{bucket_name}/{destino}")
    try:
        cliente = storage.Client()
        bucket = cliente.bucket(bucket_name)
        blob = bucket.blob(destino)
        blob.upload_from_filename(str(ruta_local))
        log.info(f"  ✓ Disponible en: gs://{bucket_name}/{destino}")
    except Exception as e:
        raise ExtractError(f"Error al subir a GCS: {e}") from e


# MAIN


def _configurar_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extrae el Bike Sharing Dataset (UCI), valida y guarda localmente. "
            "Si GCS_BUCKET_NAME está definido, también sube los archivos a GCS."
        )
    )
    parser.add_argument(
        "--formato",
        choices=["csv", "parquet"],
        default="csv",
        help="Formato de salida (default: csv)",
    )
    parser.add_argument(
        "--skip-gcs",
        action="store_true",
        help="No subir a GCS aunque GCS_BUCKET_NAME esté configurado",
    )
    args = parser.parse_args()

    _configurar_logging()
    load_dotenv()

    log.info("=" * 55)
    log.info("  EXTRACCIÓN — Bike Sharing Dataset (UCI)")
    log.info("  Autor: Daniela Caro — Data Engineer Python")
    log.info("=" * 55)

    try:
        dataframes = obtener_dataframes_uci()

        rutas_local: list[Path] = []
        for nombre, df in dataframes.items():
            validar_dataset(nombre, df)
            ruta = guardar_local(nombre, df, args.formato)
            rutas_local.append(ruta)

        if GCS_BUCKET_NAME and not args.skip_gcs:
            for ruta in rutas_local:
                upload_to_gcs(ruta, GCS_BUCKET_NAME)
        else:
            log.info(
                "  • GCS_BUCKET_NAME no configurado o --skip-gcs activo: "
                "se omite la subida a GCS."
            )
    except ExtractError as e:
        log.error(f"Extracción abortada: {e}")
        return 1

    log.info("=" * 55)
    log.info("  Extracción completada exitosamente ✓")
    log.info(f"  Archivos en: {OUTPUT_DIR}/")
    for ruta in rutas_local:
        log.info(f"    → {ruta}")
    log.info("=" * 55)

    if "day.csv" in dataframes:
        log.info("")
        log.info("── Vista previa — day.csv ───────────────────────────")
        log.info(dataframes["day.csv"].head(3).to_string())
        log.info(f"\nColumnas: {list(dataframes['day.csv'].columns)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
