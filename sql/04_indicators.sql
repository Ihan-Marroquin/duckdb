-- Ejercicio 7: los indicadores se exportan y visualizan con run_analysis.py.
SELECT file_year, file_month, taxi_type, COUNT(*) AS trips
FROM valid_trips GROUP BY ALL ORDER BY ALL;

SELECT file_year, taxi_type,
       COUNT(*) AS trips,
       ROUND(SUM(total_amount), 2) AS revenue_usd,
       ROUND(AVG(total_amount), 2) AS avg_total_usd,
       ROUND(AVG(trip_distance), 2) AS avg_distance_miles,
       ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes,
       ROUND(AVG(CASE WHEN payment_type = 1 AND fare_amount > 0
                      THEN 100.0 * tip_amount / fare_amount END), 2) AS avg_card_tip_pct,
       ROUND(100.0 * AVG(CASE WHEN dayofweek(pickup_datetime) IN (0, 6)
                              THEN 1 ELSE 0 END), 2) AS weekend_share_pct
FROM valid_trips GROUP BY ALL ORDER BY ALL;

SELECT taxi_type, payment_type, COUNT(*) AS trips
FROM valid_trips GROUP BY ALL ORDER BY taxi_type, trips DESC;

SELECT taxi_type, hour(pickup_datetime) AS pickup_hour, COUNT(*) AS trips
FROM valid_trips GROUP BY ALL ORDER BY taxi_type, pickup_hour;
