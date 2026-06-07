CREATE OR REPLACE TABLE
`mci506-bicimad-clima-v2.bike_sharing_dw.silver_day`
AS

WITH cleaned AS (

SELECT

SAFE_CAST(instant AS INT64) AS ride_id,

dteday AS ride_date,

SAFE_CAST(season AS INT64) AS season,

SAFE_CAST(yr AS INT64) AS year_flag,

SAFE_CAST(mnth AS INT64) AS month,

SAFE_CAST(holiday AS INT64) AS holiday,

SAFE_CAST(weekday AS INT64) AS weekday,

SAFE_CAST(workingday AS INT64) AS workingday,

SAFE_CAST(weathersit AS INT64) AS weather_situation,

SAFE_CAST(temp AS FLOAT64) AS temperature,

SAFE_CAST(atemp AS FLOAT64) AS feels_like_temperature,

SAFE_CAST(hum AS FLOAT64) AS humidity,

SAFE_CAST(windspeed AS FLOAT64) AS windspeed,

SAFE_CAST(casual AS INT64) AS casual_users,

SAFE_CAST(registered AS INT64) AS registered_users,

SAFE_CAST(cnt AS INT64) AS total_rides

FROM
`mci506-bicimad-clima-v2.bike_sharing_dw.bronze_day`

),

dedup AS (

SELECT *

FROM (

SELECT
*,
ROW_NUMBER() OVER(
PARTITION BY ride_id
ORDER BY ride_date DESC
) rn

FROM cleaned

)

WHERE rn = 1

)

SELECT * EXCEPT(rn)
FROM dedup;
--Creamos la capa Silver para el dataset day

CREATE OR REPLACE TABLE
`mci506-bicimad-clima-v2.bike_sharing_dw.silver_hour`
AS

WITH cleaned AS (

SELECT

SAFE_CAST(instant AS INT64) AS ride_id,

dteday AS ride_date,

SAFE_CAST(hr AS INT64) AS ride_hour,

SAFE_CAST(season AS INT64) AS season,

SAFE_CAST(yr AS INT64) AS year_flag,

SAFE_CAST(mnth AS INT64) AS month,

SAFE_CAST(holiday AS INT64) AS holiday,

SAFE_CAST(weekday AS INT64) AS weekday,

SAFE_CAST(workingday AS INT64) AS workingday,

SAFE_CAST(weathersit AS INT64) AS weather_situation,

SAFE_CAST(temp AS FLOAT64) AS temperature,

SAFE_CAST(atemp AS FLOAT64) AS feels_like_temperature,

SAFE_CAST(hum AS FLOAT64) AS humidity,

SAFE_CAST(windspeed AS FLOAT64) AS windspeed,

SAFE_CAST(casual AS INT64) AS casual_users,

SAFE_CAST(registered AS INT64) AS registered_users,

SAFE_CAST(cnt AS INT64) AS total_rides

FROM
`mci506-bicimad-clima-v2.bike_sharing_dw.bronze_hour`

),

dedup AS (

SELECT *

FROM (

SELECT
*,
ROW_NUMBER() OVER(
PARTITION BY ride_id
ORDER BY ride_date DESC
) rn

FROM cleaned

)

WHERE rn = 1

)

SELECT * EXCEPT(rn)
FROM dedup;

--Crea el dataset de la capa Silver para day