import io
import os
import sys
import zipfile
import argparse
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constantes ───────────────

DATASET_URL  = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
CSV_FILES    = ["day.csv", "hour.csv"]
MIN_FILAS    = 100
MIN_COLUMNAS = 5
OUTPUT_DIR   = Path("data/raw")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")



# 1. DESCARGA

def descargar_zip(url: str) -> bytes:
    log.info(f"Descargando dataset desde UCI...")
    log.info(f"  URL: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; mci506-extract/1.0)"}
    try:
        respuesta = requests.get(url, headers=headers, timeout=60)
        respuesta.raise_for_status()
    except requests.exceptions.HTTPError as e:
        log.error(f"Error HTTP al descargar: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        log.error("Sin conexión a internet o URL inaccesible.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        log.error("Tiempo de espera agotado. Intenta de nuevo.")
        sys.exit(1)

    log.info(f"Descarga completada — {len(respuesta.content) / 1024:.1f} KB")
    return respuesta.content


# 2. EXTRACCIÓN DEL ZIP


def extraer_dataframes(contenido_zip: bytes) -> dict[str, pd.DataFrame]:

    log.info("Extrayendo archivos del ZIP...")
    dataframes = {}
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
                    log.info(f"  ✓ {nombre}: {df.shape[0]} filas × {df.shape[1]} columnas")
    except zipfile.BadZipFile:
        log.error("El contenido descargado no es un ZIP válido.")
        sys.exit(1)

    return dataframes


# 3. VALIDACIÓN


def validar_dataset(nombre: str, df: pd.DataFrame) -> None:

    log.info(f"Validando {nombre}...")
    errores = []

    if df.shape[0] < MIN_FILAS:
        errores.append(f"  ✗ Filas: {df.shape[0]} (mínimo requerido: {MIN_FILAS})")
    else:
        log.info(f"  ✓ Filas    : {df.shape[0]} >= {MIN_FILAS}")

    if df.shape[1] < MIN_COLUMNAS:
        errores.append(f"  ✗ Columnas: {df.shape[1]} (mínimo requerido: {MIN_COLUMNAS})")
    else:
        log.info(f"  ✓ Columnas : {df.shape[1]} >= {MIN_COLUMNAS}")

    nulos = df.isnull().sum().sum()
    if nulos > 0:
        log.warning(f"  ⚠ Valores nulos detectados: {nulos} — revisar antes de transformar")
    else:
        log.info(f"  ✓ Sin valores nulos")

    if errores:
        for err in errores:
            log.error(err)
        sys.exit(1)

    log.info(f"  ✓ {nombre} validado correctamente")



    # 4. GUARDADO LOCAL
    

def guardar_local(nombre: str, df: pd.DataFrame, formato: str) -> Path:
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(nombre).stem  # "day" o "hour"

    if formato == "parquet":
        ruta = OUTPUT_DIR / f"{stem}.parquet"
        df.to_parquet(ruta, index=False)
    else:
        ruta = OUTPUT_DIR / f"{stem}.csv"
        df.to_csv(ruta, index=False)

    log.info(f"  ✓ Guardado local: {ruta}")
    return ruta

# 5. SUBIDA A GCS


def upload_to_gcs(ruta_local: Path, bucket_name: str) -> None:
 
    try:
        from google.cloud import storage
    except ImportError:
        log.error("Ejecuta: pip install google-cloud-storage")
        sys.exit(1)

    destino = f"raw/{ruta_local.name}"
    log.info(f"Subiendo a GCS: gs://{bucket_name}/{destino}")
    try:
        cliente = storage.Client()
        bucket  = cliente.bucket(bucket_name)
        blob    = bucket.blob(destino)
        blob.upload_from_filename(str(ruta_local))
        log.info(f"  ✓ Disponible en: gs://{bucket_name}/{destino}")
    except Exception as e:
        log.error(f"Error al subir a GCS: {e}")
        sys.exit(1)



# MAIN


def main():
    parser = argparse.ArgumentParser(
        description="Extrae el Bike Sharing Dataset (UCI) y genera archivos locales."
    )
    parser.add_argument(
        "--formato",
        choices=["csv", "parquet"],
        default="csv",
        help="Formato de salida (default: csv)",
    )
    args = parser.parse_args()

    log.info("=" * 55)
    log.info("  EXTRACCIÓN — Bike Sharing Dataset (UCI)")
    log.info("  Autor: Daniela Caro — Data Engineer Python")
    log.info("=" * 55)

    contenido  = descargar_zip(DATASET_URL)
    dataframes = extraer_dataframes(contenido)
    rutas_local = []

    for nombre, df in dataframes.items():
        validar_dataset(nombre, df)
        ruta = guardar_local(nombre, df, args.formato)
        rutas_local.append(ruta)

    
    # for ruta in rutas_local:
    #     upload_to_gcs(ruta, GCS_BUCKET_NAME)

    log.info("=" * 55)
    log.info("  Extracción completada exitosamente ✓")
    log.info(f"  Archivos en: {OUTPUT_DIR}/")
    for ruta in rutas_local:
        log.info(f"    → {ruta}")
    log.info("=" * 55)

    print("\n── Vista previa — day.csv ───────────────────────────")
    print(dataframes["day.csv"].head(3).to_string())
    print(f"\nColumnas: {list(dataframes['day.csv'].columns)}")


if __name__ == "__main__":
    main()