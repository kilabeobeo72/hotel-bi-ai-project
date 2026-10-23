-- File: lab_project/dbt/hotel_dw/models/marts/dim_customer.sql
{{ config(
    materialized='table',
    schema='dds'
) }}

WITH customer_transformed AS (
    SELECT
        COALESCE(country_code, 'UNK') AS country_code,
        customer_type,
        CAST(is_repeated_guest AS INT) AS is_repeated_guest,
        CASE
            WHEN (COALESCE(children, 0) + COALESCE(babies, 0)) > 0 THEN 'Family'
            WHEN COALESCE(adults, 0) = 1 THEN 'Solo'
            WHEN COALESCE(adults, 0) = 2 THEN 'Couple'
            ELSE 'Group'
        END AS guest_group_type
    FROM {{ ref('stg_hotel_bookings') }}
),

distinct_customers AS (
    SELECT DISTINCT
        country_code,
        customer_type,
        is_repeated_guest,
        guest_group_type
    FROM customer_transformed
)

SELECT
    MD5(
        CONCAT_WS(
            '|',
            country_code,
            customer_type,
            CAST(is_repeated_guest AS TEXT),
            guest_group_type
        )
    ) AS customer_key,
    country_code,
    customer_type,
    is_repeated_guest,
    guest_group_type
FROM distinct_customers