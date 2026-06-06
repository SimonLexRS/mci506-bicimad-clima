CREATE OR REPLACE EXTERNAL TABLE
`mci506-bicimad-clima-v2.bike_sharing_dw.bronze_hour`
OPTIONS (
  format = 'CSV',
  uris = ['gs://bike_sharing_v2/raw/hour.csv'],
  skip_leading_rows = 1
);
-- esto es para la hour

CREATE OR REPLACE EXTERNAL TABLE
`mci506-bicimad-clima-v2.bike_sharing_dw.bronze_day`
OPTIONS (
  format = 'CSV',
  uris = ['gs://bike_sharing_v2/raw/day.csv'],
  skip_leading_rows = 1
);
-- Esto es para el day