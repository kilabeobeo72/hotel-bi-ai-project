-- File: lab_project/dbt/hotel_dw/models/marts/dim_room_policy.sql
{{ config(
    materialized='table',
    schema='dds'
) }}

WITH distinct_policies AS (
    SELECT DISTINCT
        reserved_room_type,
        assigned_room_type,
        CASE
            WHEN reserved_room_type <> assigned_room_type THEN TRUE
            ELSE FALSE
        END AS is_room_upgraded,
        meal_code,
        CASE
            WHEN meal_code = 'BB' THEN 'Bed & Breakfast'
            WHEN meal_code = 'HB' THEN 'Half Board (Breakfast & Dinner)'
            WHEN meal_code = 'FB' THEN 'Full Board (Breakfast, Lunch & Dinner)'
            WHEN meal_code = 'SC' THEN 'Self Catering (No Meal Package)'
            ELSE 'Undefined / No Meal Package'
        END AS meal_description,
        deposit_type
    FROM {{ ref('stg_hotel_bookings') }}
)

SELECT
    MD5(
        CONCAT_WS(
            '|',
            reserved_room_type,
            assigned_room_type,
            meal_code,
            deposit_type
        )
    ) AS policy_key,
    reserved_room_type,
    assigned_room_type,
    is_room_upgraded,
    meal_code,
    meal_description,
    deposit_type
FROM distinct_policies