"""Carga de datos procesados a BigQuery (capas Silver/Gold).

Lee los archivos de data/processed/ y los inserta en las tablas destino
de BigQuery del proyecto.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

INPUT_DIR = Path("data/processed")
BIGQUERY_PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID", "")
TABLE_SILVER = os.getenv("TABLE_SILVER", "bicimad_clima.silver_bike_sharing")
TABLE_GOLD = os.getenv("TABLE_GOLD", "bicimad_clima.gold_bike_sharing_daily")

log = logging.getLogger(__name__)


class LoadError(RuntimeError):
    """Error recuperable durante la carga."""


def cargar_procesados(input_dir: Path) -> dict[str, Path]:
    log.info(f"Buscando archivos en {input_dir}/...")
    rutas: dict[str, Path] = {}
    for nombre in ["day.csv", "hour.csv", "day.parquet", "hour.parquet"]:
        ruta = input_dir / nombre
        if ruta.exists():
            rutas[nombre] = ruta
            log.info(f"  ✓ Encontrado: {ruta}")
    if not rutas:
        log.warning("  ⚠ No se encontraron archivos procesados.")
    return rutas


def subir_a_bigquery(ruta: Path, tabla_destino: str, project_id: str) -> None:
    try:
        from google.cloud import bigquery
    except ImportError as e:
        raise LoadError(
            "Falta google-cloud-bigquery. "
            "Instálala con: pip install google-cloud-bigquery"
        ) from e

    log.info(f"Subiendo {ruta.name} → {tabla_destino} (project={project_id})")
    cliente = bigquery.Client(project=project_id or None)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    try:
        if ruta.suffix == ".parquet":
            job = cliente.load_table_from_file(
                open(ruta, "rb"), tabla_destino, job_config=job_config
            )
        else:
            job = cliente.load_table_from_file(
                open(ruta, "rb"), tabla_destino, job_config=job_config
            )
        job.result()
        log.info(f"  ✓ Cargado en {tabla_destino}")
    except Exception as e:
        raise LoadError(f"Error al cargar en BigQuery: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Carga los datos procesados de data/processed/ "
            "a BigQuery (capas Silver/Gold)."
        )
    )
    parser.add_argument(
        "--capa",
        choices=["silver", "gold", "ambas"],
        default="ambas",
        help="Capa destino en BigQuery (default: ambas)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("=" * 55)
    log.info("  CARGA — BigQuery Silver/Gold")
    log.info("=" * 55)

    if not BIGQUERY_PROJECT_ID:
        log.error(
            "BIGQUERY_PROJECT_ID no está configurado. "
            "Configúralo en .env antes de ejecutar la carga."
        )
        return 1

    try:
        archivos = cargar_procesados(INPUT_DIR)
        if not archivos:
            raise LoadError(
                "No hay datos procesados en data/processed/. "
                "Ejecuta transform.py primero."
            )

        tabla_objetivo = TABLE_SILVER
        if args.capa == "gold":
            tabla_objetivo = TABLE_GOLD

        for nombre, ruta in archivos.items():
            if nombre.startswith("hour") and args.capa == "gold":
                log.info(f"  • {nombre} se omite en capa gold (solo daily).")
                continue
            subir_a_bigquery(ruta, tabla_objetivo, BIGQUERY_PROJECT_ID)
    except LoadError as e:
        log.error(f"Carga abortada: {e}")
        return 1

    log.info("=" * 55)
    log.info("  Carga completada exitosamente ✓")
    log.info("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
