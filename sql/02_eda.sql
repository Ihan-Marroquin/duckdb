-- Ejercicio 4: consultas que responden preguntas analiticas.
SELECT file_year, file_month, taxi_type,
       COUNT(*) AS trips,
       ROUND(AVG(trip_distance), 2) AS avg_distance_miles,
       ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes,
       ROUND(AVG(total_amount), 2) AS avg_total_usd
FROM valid_trips GROUP BY ALL ORDER BY file_year, file_month, taxi_type;

SELECT taxi_type, payment_type, COUNT(*) AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY taxi_type), 2) AS share_pct
FROM valid_trips GROUP BY ALL ORDER BY taxi_type, trips DESC;

SELECT taxi_type, hour(pickup_datetime) AS pickup_hour, COUNT(*) AS trips
FROM valid_trips GROUP BY ALL ORDER BY taxi_type, pickup_hour;

SELECT taxi_type,
       quantile_cont(trip_distance, [0.5, 0.9, 0.99]) AS distance_quantiles,
       quantile_cont(duration_minutes, [0.5, 0.9, 0.99]) AS duration_quantiles,
       quantile_cont(total_amount, [0.5, 0.9, 0.99]) AS total_quantiles
FROM valid_trips GROUP BY taxi_type;
