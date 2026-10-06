-- Vista normalizada sobre archivos Parquet, sin importacion previa.
-- union_by_name tolera columnas nuevas o ausentes entre meses/anios.
CREATE OR REPLACE VIEW trips AS
SELECT
    'yellow' AS taxi_type,
    filename,
    regexp_extract(filename, '(\d{4})-(\d{2})\.parquet$', 1)::INTEGER AS file_year,
    regexp_extract(filename, '(\d{4})-(\d{2})\.parquet$', 2)::INTEGER AS file_month,
    VendorID AS vendor_id,
    tpep_pickup_datetime AS pickup_datetime,
    tpep_dropoff_datetime AS dropoff_datetime,
    passenger_count,
    trip_distance,
    RatecodeID AS rate_code_id,
    store_and_fwd_flag,
    PULocationID AS pickup_location_id,
    DOLocationID AS dropoff_location_id,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    Airport_fee AS airport_fee,
    NULL::DOUBLE AS ehail_fee,
    NULL::BIGINT AS trip_type
FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name=true, filename=true)

UNION ALL BY NAME

SELECT
    'green' AS taxi_type,
    filename,
    regexp_extract(filename, '(\d{4})-(\d{2})\.parquet$', 1)::INTEGER AS file_year,
    regexp_extract(filename, '(\d{4})-(\d{2})\.parquet$', 2)::INTEGER AS file_month,
    VendorID AS vendor_id,
    lpep_pickup_datetime AS pickup_datetime,
    lpep_dropoff_datetime AS dropoff_datetime,
    passenger_count,
    trip_distance,
    RatecodeID AS rate_code_id,
    store_and_fwd_flag,
    PULocationID AS pickup_location_id,
    DOLocationID AS dropoff_location_id,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    NULL::DOUBLE AS airport_fee,
    ehail_fee,
    trip_type
FROM read_parquet('data/raw/green/*/*.parquet', union_by_name=true, filename=true);

CREATE OR REPLACE VIEW valid_trips AS
SELECT *,
       date_diff('minute', pickup_datetime, dropoff_datetime) AS duration_minutes
FROM trips
WHERE pickup_datetime IS NOT NULL
  AND dropoff_datetime IS NOT NULL
  AND year(pickup_datetime) = file_year
  AND dropoff_datetime > pickup_datetime
  AND dropoff_datetime <= pickup_datetime + INTERVAL '24 hours'
  AND trip_distance >= 0
  AND total_amount >= 0;
