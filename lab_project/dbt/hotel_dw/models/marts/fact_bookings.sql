-- Phụ trách chính (Giai đoạn 1): Phạm Ngọc Thanh
-- Bảng Sự kiện Đặt phòng (Fact Bookings)
-- Grain: Mỗi dòng đại diện cho 01 giao dịch đặt phòng (booking_id)

WITH stg AS (
    SELECT * FROM {{ ref('stg_hotel_bookings') }}
)

SELECT
    stg.booking_id,
    MD5(stg.hotel_name) AS hotel_key,
    MD5(CONCAT_WS('|', stg.country_code, stg.customer_type, stg.is_repeated_guest)) AS customer_key,
    MD5(CONCAT_WS('|', stg.market_segment, stg.distribution_channel, stg.agent_code, stg.company_code)) AS channel_key,
    MD5(CONCAT_WS('|', stg.reserved_room_type, stg.assigned_room_type, stg.meal_code, stg.deposit_type)) AS policy_key,
    CAST(TO_CHAR(stg.arrival_date, 'YYYYMMDD') AS INTEGER) AS arrival_date_key,
    CAST(TO_CHAR(stg.reservation_status_date, 'YYYYMMDD') AS INTEGER) AS status_date_key,

    -- Các chỉ số định lượng (Measures)
    stg.is_canceled,
    stg.lead_time,
    CASE
        WHEN stg.lead_time <= 7 THEN '1. Short (0-7 days)'
        WHEN stg.lead_time <= 30 THEN '2. Medium (8-30 days)'
        WHEN stg.lead_time <= 90 THEN '3. Long (31-90 days)'
        WHEN stg.lead_time <= 180 THEN '4. Very Long (91-180 days)'
        ELSE '5. Extreme (>180 days)'
    END AS lead_time_group,
    stg.stays_in_weekend_nights,
    stg.stays_in_week_nights,
    stg.total_nights,
    stg.adults,
    stg.children,
    stg.babies,
    (stg.adults + stg.children + stg.babies) AS total_guests,
    stg.adr,
    ROUND(stg.adr * stg.total_nights, 2) AS gross_revenue,
    CASE WHEN stg.is_canceled = 0 THEN ROUND(stg.adr * stg.total_nights, 2) ELSE 0 END AS actual_revenue,
    CASE WHEN stg.is_canceled = 1 THEN ROUND(stg.adr * stg.total_nights, 2) ELSE 0 END AS revenue_loss,
    stg.booking_changes,
    stg.days_in_waiting_list,
    stg.required_car_parking_spaces,
    stg.total_of_special_requests,
    stg.reservation_status,
    stg.source_file,
    stg.ingested_at
FROM stg
