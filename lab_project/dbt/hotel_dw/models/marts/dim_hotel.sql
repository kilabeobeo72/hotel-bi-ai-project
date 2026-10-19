-- Phụ trách chính (Giai đoạn 1): Phạm Ngọc Thanh
WITH distinct_hotels AS (
    SELECT DISTINCT hotel_name FROM {{ ref('stg_hotel_bookings') }}
)
SELECT
    MD5(hotel_name) AS hotel_key,
    hotel_name,
    CASE WHEN hotel_name = 'Resort Hotel' THEN 'Leisure & Vacation Resort' ELSE 'Urban & Business Hotel' END AS hotel_category
FROM distinct_hotels
