-- Ejercicio 6: tabla fisica usada por Metabase y el benchmark.
CREATE OR REPLACE TABLE trips_materialized AS SELECT * FROM trips;
CREATE INDEX IF NOT EXISTS idx_trips_year_type
    ON trips_materialized(file_year, taxi_type);
