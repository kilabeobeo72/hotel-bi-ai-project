-- File: lab_project/dbt/hotel_dw/models/marts/dim_hotel.sql
{{ config(
    materialized='table',
    schema='dds'
) }}

WITH distinct_hotels AS (
    SELECT DISTINCT
        hotel_name
    FROM {{ ref('stg_hotel_bookings') }}
    WHERE hotel_name IS NOT NULL
)

SELECT
    MD5(hotel_name) AS hotel_key,
    hotel_name,
    CASE
        WHEN hotel_name = 'Resort Hotel' THEN 'Resort'
        WHEN hotel_name = 'City Hotel' THEN 'City'
        ELSE 'Other'
    END AS hotel_category
FROM distinct_hotels