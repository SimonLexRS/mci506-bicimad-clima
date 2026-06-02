"""Extracción del Bike Sharing Dataset (UCI).

Descarga el ZIP público, valida su contenido, lo guarda localmente y,
si GCS_BUCKET_NAME está configurado, lo sube a GCS.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import logging
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
import os

DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
)
CSV_FILES = ["day.csv", "hour.csv"]
MIN_FILAS = 100
MIN_COLUMNAS = 5
OUTPUT_DIR = Path("data/raw")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
REQUEST_TIMEOUT_S = 60
USER_AGENT = "Mozilla/5.0 (compatible; mci506-extract/1.0)"

log = logging.getLogger(__name__)


class ExtractError(RuntimeError):
    """Error recuperable durante la extracción."""


# 1. DESCARGA


def descargar_zip(url: str) -> bytes:
    log.info("Descargando dataset desde UCI...")
    log.info(f"  URL: {url}")
    headers = {"User-Agent": USER_AGENT}
    try:
        respuesta = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_S)
        respuesta.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise ExtractError(f"Error HTTP al descargar: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise ExtractError("Sin conexión a internet o URL inaccesible.") from e
    except requests.exceptions.Timeout as e:
        raise ExtractError("Tiempo de espera agotado. Intenta de nuevo.") from e

    size_kb = len(respuesta.content) / 1024
    log.info(f"Descarga completada — {size_kb:.1f} KB")
    return respuesta.content


def verificar_zip(contenido: bytes) -> None:
    md5 = hashlib.md5(contenido).hexdigest()
    log.info(f"  ✓ MD5 del ZIP: {md5} (traza de auditoría)")


# 2. EXTRACCIÓN DEL ZIP


def extraer_dataframes(contenido_zip: bytes) -> dict[str, pd.DataFrame]:
    log.info("Extrayendo archivos del ZIP...")
    dataframes: dict[str, pd.DataFrame] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(contenido_zip)) as z:
            disponibles = z.namelist()
            log.info(f"  Archivos en ZIP: {disponibles}")
            for nombre in CSV_FILES:
                if nombre not in disponibles:
                    log.warning(f"  ⚠ '{nombre}' no encontrado en el ZIP, se omite.")
                    continue
                with z.open(nombre) as f:
                    df = pd.read_csv(f)
                    dataframes[nombre] = df
                    log.info(
                        f"  ✓ {nombre}: {df.shape[0]} filas × "
                        f"{df.shape[1]} columnas"
                    )
    except zipfile.BadZipFile as e:
        raise ExtractError("El contenido descargado no es un ZIP válido.") from e

    return dataframes


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
        contenido = descargar_zip(DATASET_URL)
        verificar_zip(contenido)
        dataframes = extraer_dataframes(contenido)
        if not dataframes:
            raise ExtractError(
                "No se pudo extraer ningún CSV del ZIP descargado."
            )

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
