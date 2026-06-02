# mci506-bicimad-clima

Pipeline de extracción, transformación y carga (ETL) para datos de BiciMAD
y clima, desarrollado como parte del Módulo 7 del MCI 506.

## Estructura

```
.
├── data/
│   └── raw/         # Datos crudos descargados por extract.py
├── scripts/
│   ├── extract.py   # Descarga, validación y carga opcional a GCS
│   ├── transform.py # Limpieza y unión de datos (pendiente)
│   └── load.py      # Carga a BigQuery / GCS (pendiente)
├── requirements.txt
├── .env.example
└── README.md
```

## Fuente de datos

| Archivo | Fuente | URL | Licencia |
| --- | --- | --- | --- |
| `day.csv` / `hour.csv` | UCI Machine Learning Repository — Bike Sharing Dataset | https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset | Para uso académico |

> El dataset de UCI se utiliza como **placeholder público** mientras se
> integran las fuentes definitivas (API de BiciMAD y AEMET). La estructura
> del pipeline no cambia.

## Columnas (`day.csv` / `hour.csv`)

| Columna | Tipo | Descripción |
| --- | --- | --- |
| `instant` | int | Índice de registro |
| `dteday` | date | Fecha |
| `season` | int | 1=primavera, 2=verano, 3=otoño, 4=invierno |
| `yr` | int | 0=2011, 1=2012 |
| `mnth` | int | Mes (1–12) |
| `holiday` | int | 1 si es festivo |
| `weekday` | int | Día de la semana |
| `workingday` | int | 1 si es día laborable |
| `weathersit` | int | 1=bueno, 2=nublado, 3=lluvia, 4=tormenta |
| `temp` | float | Temperatura normalizada (°C/41 máx.) |
| `atemp` | float | Sensación térmica normalizada |
| `hum` | float | Humedad normalizada |
| `windspeed` | float | Viento normalizado |
| `casual` | int | Usuarios ocasionales |
| `registered` | int | Usuarios registrados |
| `cnt` | int | Total de alquileres (`casual + registered`) |

`hour.csv` añade las mismas columnas más `hr` (hora 0–23).

## Configuración

Copia `.env.example` a `.env` y rellena los valores. **No commitees `.env`.**

```ini
GCS_BUCKET_NAME=
GOOGLE_APPLICATION_CREDENTIALS=
```

- `GCS_BUCKET_NAME` — nombre del bucket destino. Si está vacío, `extract.py`
  omite la subida a GCS.
- `GOOGLE_APPLICATION_CREDENTIALS` — ruta al JSON de la service account de GCP.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

## Uso

### Extracción

```bash
python scripts/extract.py                  # CSV, sube a GCS si está configurado
python scripts/extract.py --formato parquet
python scripts/extract.py --skip-gcs       # no sube a GCS
```

Salida esperada:

- `data/raw/day.csv` y `data/raw/hour.csv` (o `.parquet`)
- Subida opcional a `gs://<bucket>/raw/...`

### Transformación (pendiente)

```bash
python scripts/transform.py
```

### Carga a BigQuery (pendiente)

```bash
python scripts/load.py
```

## Estado del proyecto

- [x] Estructura inicial del repositorio
- [x] `extract.py` funcional con descarga, validación y carga opcional a GCS
- [x] `requirements.txt` y `.gitignore`
- [ ] `transform.py`
- [ ] `load.py` (BigQuery / GCS Silver-Gold)
- [ ] Dashboard y documentación final

## Equipo

- Daniela Caro — Data Engineer Python
- Simon Alex Rodriguez — Revisión y orquestación
