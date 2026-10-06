-- Ejercicio 3: exploracion directa de Parquet.
SELECT taxi_type, file_year, COUNT(DISTINCT filename) AS files, COUNT(*) AS rows
FROM trips GROUP BY ALL ORDER BY file_year, taxi_type;

DESCRIBE SELECT * FROM trips;

SELECT * FROM trips USING SAMPLE 10 ROWS;

-- Controles de calidad. Las categorias no son excluyentes.
SELECT
    taxi_type,
    file_year,
    COUNT(*) AS rows,
    count_if(pickup_datetime IS NULL OR dropoff_datetime IS NULL) AS null_timestamps,
    count_if(year(pickup_datetime) <> file_year) AS pickup_outside_file_year,
    count_if(dropoff_datetime <= pickup_datetime) AS nonpositive_duration,
    count_if(dropoff_datetime > pickup_datetime + INTERVAL '24 hours') AS duration_over_24h,
    count_if(trip_distance <= 0) AS nonpositive_distance,
    count_if(total_amount < 0) AS negative_total,
    count_if(passenger_count IS NULL OR passenger_count <= 0) AS missing_or_zero_passengers
FROM trips GROUP BY ALL ORDER BY file_year, taxi_type;
