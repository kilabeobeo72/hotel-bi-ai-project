-- Phụ trách chính (Giai đoạn 1): Phạm Ngọc Thanh
-- Bảng chiều Khách hàng & Quốc tịch (Dim Customer)

WITH distinct_customers AS (
    SELECT DISTINCT
        country_code,
        customer_type,
        is_repeated_guest
    FROM {{ ref('stg_hotel_bookings') }}
)

SELECT
    MD5(CONCAT_WS('|', country_code, customer_type, is_repeated_guest)) AS customer_key,
    country_code,
    customer_type,
    is_repeated_guest,
    CASE WHEN is_repeated_guest = 1 THEN 'Returning Guest' ELSE 'First-Time Guest' END AS loyalty_status
FROM distinct_customers
