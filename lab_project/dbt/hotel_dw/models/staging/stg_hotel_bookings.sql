-- Phụ trách chính (Giai đoạn 1): Đào Trung Kiên
-- Làm sạch và chuẩn hóa dữ liệu từ stage.raw_hotel_bookings

WITH raw_data AS (
    SELECT *
    FROM {{ source('stage', 'raw_hotel_bookings') }}
),

cleaned AS (
    SELECT
        COALESCE(booking_uid, MD5(CONCAT_WS('|', hotel, arrival_date_year, arrival_date_month, arrival_date_day_of_month, lead_time, adr, country))) AS booking_id,
        TRIM(hotel) AS hotel_name,
        CAST(is_canceled AS INTEGER) AS is_canceled,
        CAST(lead_time AS INTEGER) AS lead_time,
        TO_DATE(
            CONCAT(arrival_date_year, '-', arrival_date_month, '-', arrival_date_day_of_month),
            'YYYY-FMMonth-DD'
        ) AS arrival_date,
        CAST(arrival_date_year AS INTEGER) AS arrival_year,
        TRIM(arrival_date_month) AS arrival_month_name,
        CAST(arrival_date_week_number AS INTEGER) AS arrival_week_number,
        CAST(arrival_date_day_of_month AS INTEGER) AS arrival_day_of_month,
        CAST(stays_in_weekend_nights AS INTEGER) AS stays_in_weekend_nights,
        CAST(stays_in_week_nights AS INTEGER) AS stays_in_week_nights,
        (CAST(stays_in_weekend_nights AS INTEGER) + CAST(stays_in_week_nights AS INTEGER)) AS total_nights,
        CAST(adults AS INTEGER) AS adults,
        COALESCE(CAST(NULLIF(CAST(children AS TEXT), 'NA') AS NUMERIC)::INTEGER, 0) AS children,
        CAST(babies AS INTEGER) AS babies,
        TRIM(COALESCE(meal, 'Undefined')) AS meal_code,
        UPPER(TRIM(COALESCE(NULLIF(country, 'NULL'), 'UNK'))) AS country_code,
        TRIM(COALESCE(market_segment, 'Undefined')) AS market_segment,
        TRIM(COALESCE(distribution_channel, 'Undefined')) AS distribution_channel,
        CAST(is_repeated_guest AS INTEGER) AS is_repeated_guest,
        CAST(previous_cancellations AS INTEGER) AS previous_cancellations,
        CAST(previous_bookings_not_canceled AS INTEGER) AS previous_bookings_not_canceled,
        TRIM(reserved_room_type) AS reserved_room_type,
        TRIM(assigned_room_type) AS assigned_room_type,
        CAST(booking_changes AS INTEGER) AS booking_changes,
        TRIM(COALESCE(deposit_type, 'No Deposit')) AS deposit_type,
        TRIM(COALESCE(NULLIF(CAST(agent AS TEXT), 'NULL'), '0')) AS agent_code,
        TRIM(COALESCE(NULLIF(CAST(company AS TEXT), 'NULL'), '0')) AS company_code,
        CAST(days_in_waiting_list AS INTEGER) AS days_in_waiting_list,
        TRIM(COALESCE(customer_type, 'Transient')) AS customer_type,
        CAST(adr AS NUMERIC(12, 2)) AS adr,
        CAST(required_car_parking_spaces AS INTEGER) AS required_car_parking_spaces,
        CAST(total_of_special_requests AS INTEGER) AS total_of_special_requests,
        TRIM(reservation_status) AS reservation_status,
        CAST(reservation_status_date AS DATE) AS reservation_status_date,
        source_file,
        ingested_at
    FROM raw_data
    WHERE CAST(adr AS NUMERIC) >= 0
      AND (CAST(adults AS INTEGER) + COALESCE(CAST(NULLIF(CAST(children AS TEXT), 'NA') AS NUMERIC)::INTEGER, 0) + CAST(babies AS INTEGER)) > 0
)

SELECT * FROM cleaned
