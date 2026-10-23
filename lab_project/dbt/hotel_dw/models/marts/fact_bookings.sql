-- File: lab_project/dbt/hotel_dw/models/marts/fact_bookings.sql
{{ config(
    materialized='table',
    schema='dds'
) }}

WITH stg AS (
    SELECT
        *,
        CASE
            WHEN (COALESCE(children, 0) + COALESCE(babies, 0)) > 0 THEN 'Family'
            WHEN COALESCE(adults, 0) = 1 THEN 'Solo'
            WHEN COALESCE(adults, 0) = 2 THEN 'Couple'
            ELSE 'Group'
        END AS guest_group_type,
        -- Tính trước tổng số đêm và tổng số khách
        (COALESCE(stays_in_weekend_nights, 0) + COALESCE(stays_in_week_nights, 0)) AS total_nights,
        (COALESCE(adults, 0) + COALESCE(children, 0) + COALESCE(babies, 0)) AS total_guests
    FROM {{ ref('stg_hotel_bookings') }}
)

SELECT
    -- Primary Key của bảng Fact
    stg.booking_key,

    -- 6 Surrogate Foreign Keys nối tới 5 bảng Dimension
    dh.hotel_key,
    dc.customer_key,
    dch.channel_key,
    drp.policy_key,
    d_arr.date_key AS arrival_date_key,
    d_stat.date_key AS status_date_key,

    -- Các Measures được tính sẵn
    CAST(stg.total_nights AS INT) AS total_nights,
    CAST(stg.total_guests AS INT) AS total_guests,
    CAST(stg.adr AS NUMERIC(10, 2)) AS adr,
    CAST(ROUND(stg.adr * stg.total_nights, 2) AS NUMERIC(12, 2)) AS gross_revenue,
    CAST(
        CASE
            WHEN stg.is_canceled = 0 THEN ROUND(stg.adr * stg.total_nights, 2)
            ELSE 0.00
        END AS NUMERIC(12, 2)
    ) AS actual_revenue,
    CAST(
        CASE
            WHEN stg.is_canceled = 1 THEN ROUND(stg.adr * stg.total_nights, 2)
            ELSE 0.00
        END AS NUMERIC(12, 2)
    ) AS revenue_loss,
    CAST(stg.lead_time AS INT) AS lead_time,
    CASE
        WHEN stg.lead_time <= 7 THEN '1. Short (0-7 days)'
        WHEN stg.lead_time <= 30 THEN '2. Medium (8-30 days)'
        WHEN stg.lead_time <= 90 THEN '3. Long (31-90 days)'
        WHEN stg.lead_time <= 180 THEN '4. Very Long (91-180 days)'
        ELSE '5. Extreme (>180 days)'
    END AS lead_time_group,
    CAST(stg.is_canceled AS INT) AS is_canceled,
    CAST(stg.booking_changes AS INT) AS booking_changes,
    CAST(stg.total_of_special_requests AS INT) AS total_of_special_requests

FROM stg
INNER JOIN {{ ref('dim_hotel') }} dh
    ON stg.hotel_name = dh.hotel_name
INNER JOIN {{ ref('dim_customer') }} dc
    ON stg.country_code = dc.country_code
    AND stg.customer_type = dc.customer_type
    AND stg.is_repeated_guest = dc.is_repeated_guest
    AND stg.guest_group_type = dc.guest_group_type
INNER JOIN {{ ref('dim_channel') }} dch
    ON stg.market_segment = dch.market_segment
    AND stg.distribution_channel = dch.distribution_channel
    AND stg.agent_code = dch.agent_code
    AND stg.company_code = dch.company_code
INNER JOIN {{ ref('dim_room_policy') }} drp
    ON stg.reserved_room_type = drp.reserved_room_type
    AND stg.assigned_room_type = drp.assigned_room_type
    AND stg.meal_code = drp.meal_code
    AND stg.deposit_type = drp.deposit_type
INNER JOIN {{ ref('dim_date') }} d_arr
    ON stg.arrival_date = d_arr.full_date
INNER JOIN {{ ref('dim_date') }} d_stat
    ON stg.reservation_status_date = d_stat.full_date
