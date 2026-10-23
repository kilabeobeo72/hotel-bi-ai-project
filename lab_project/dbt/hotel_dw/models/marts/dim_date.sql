-- File: lab_project/dbt/hotel_dw/models/marts/dim_date.sql
{{ config(
    materialized='table',
    schema='dds'
) }}

WITH date_spine AS (
    SELECT
        GENERATE_SERIES(
            '2014-01-01'::DATE,
            '2018-12-31'::DATE,
            '1 day'::INTERVAL
        )::DATE AS full_date
)

SELECT
    CAST(TO_CHAR(full_date, 'YYYYMMDD') AS INT) AS date_key,
    full_date,
    CAST(EXTRACT(YEAR FROM full_date) AS INT) AS year,
    CAST(EXTRACT(QUARTER FROM full_date) AS INT) AS quarter,
    CAST(EXTRACT(MONTH FROM full_date) AS INT) AS month,
    TRIM(TO_CHAR(full_date, 'Month')) AS month_name,
    CAST(EXTRACT(WEEK FROM full_date) AS INT) AS week_of_year,
    CAST(EXTRACT(ISODOW FROM full_date) AS INT) AS day_of_week,
    CASE
        WHEN EXTRACT(ISODOW FROM full_date) IN (6, 7) THEN TRUE
        ELSE FALSE
    END AS is_weekend
FROM date_spine
ORDER BY date_key