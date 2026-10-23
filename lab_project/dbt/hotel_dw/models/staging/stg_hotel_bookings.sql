-- File: lab_project/dbt/hotel_dw/models/staging/stg_hotel_bookings.sql
{{ config(
    materialized='view'
) }}

WITH raw_source AS (
    SELECT *
    FROM {{ source('stage', 'raw_hotel_bookings') }}
),

cleaned AS (
    SELECT
        -- Tạo khóa định danh duy nhất cho mỗi giao dịch đặt phòng
        MD5(CAST(ROW_NUMBER() OVER () AS TEXT)) AS booking_key,

        -- Thông tin khách sạn
        TRIM(hotel) AS hotel_name,

        -- Thông tin trạng thái & thời gian
        CAST(COALESCE(is_canceled, 0) AS INT) AS is_canceled,
        CAST(GREATEST(COALESCE(lead_time, 0), 0) AS INT) AS lead_time,
        TO_DATE(
            CAST(arrival_date_year AS TEXT) || '-' ||
            TRIM(arrival_date_month) || '-' ||
            CAST(arrival_date_day_of_month AS TEXT),
            'YYYY-Month-DD'
        ) AS arrival_date,
        CAST(reservation_status_date AS DATE) AS reservation_status_date,
        TRIM(reservation_status) AS reservation_status,

        -- Thông tin số đêm lưu trú
        CAST(GREATEST(COALESCE(stays_in_weekend_nights, 0), 0) AS INT) AS stays_in_weekend_nights,
        CAST(GREATEST(COALESCE(stays_in_week_nights, 0), 0) AS INT) AS stays_in_week_nights,

        -- Thông tin số lượng khách
        CAST(GREATEST(COALESCE(adults, 0), 0) AS INT) AS adults,
        CAST(GREATEST(COALESCE(children, 0), 0) AS INT) AS children,
        CAST(GREATEST(COALESCE(babies, 0), 0) AS INT) AS babies,

        -- Thông tin khách hàng
        COALESCE(NULLIF(TRIM(country), ''), 'UNK') AS country_code,
        COALESCE(NULLIF(TRIM(customer_type), ''), 'Transient') AS customer_type,
        CAST(COALESCE(is_repeated_guest, 0) AS INT) AS is_repeated_guest,

        -- Thông tin kênh phân phối & đại lý
        CASE
            WHEN TRIM(market_segment) IN ('Undefined', '') OR market_segment IS NULL THEN 'Direct'
            ELSE TRIM(market_segment)
        END AS market_segment,
        CASE
            WHEN TRIM(distribution_channel) IN ('Undefined', '') OR distribution_channel IS NULL THEN 'Direct'
            ELSE TRIM(distribution_channel)
        END AS distribution_channel,
        COALESCE(
            NULLIF(REGEXP_REPLACE(CAST(agent AS TEXT), '\.0$', ''), 'NULL'),
            'No Agent'
        ) AS agent_code,
        COALESCE(
            NULLIF(REGEXP_REPLACE(CAST(company AS TEXT), '\.0$', ''), 'NULL'),
            'No Company'
        ) AS company_code,

        -- Thông tin phòng, bữa ăn & chính sách đặt cọc
        TRIM(reserved_room_type) AS reserved_room_type,
        TRIM(assigned_room_type) AS assigned_room_type,
        CASE
            WHEN TRIM(meal) IN ('Undefined', '') OR meal IS NULL THEN 'SC'
            ELSE TRIM(meal)
        END AS meal_code,
        COALESCE(NULLIF(TRIM(deposit_type), ''), 'No Deposit') AS deposit_type,

        -- Các chỉ số đo lường (Measures)
        CAST(GREATEST(COALESCE(adr, 0), 0) AS NUMERIC(10, 2)) AS adr,
        CAST(GREATEST(COALESCE(booking_changes, 0), 0) AS INT) AS booking_changes,
        CAST(GREATEST(COALESCE(total_of_special_requests, 0), 0) AS INT) AS total_of_special_requests
    FROM raw_source
)

SELECT * FROM cleaned