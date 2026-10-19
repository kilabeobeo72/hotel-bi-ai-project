-- Phụ trách chính (Giai đoạn 1): Phạm Ngọc Thanh
WITH distinct_channels AS (
    SELECT DISTINCT market_segment, distribution_channel, agent_code, company_code FROM {{ ref('stg_hotel_bookings') }}
)
SELECT
    MD5(CONCAT_WS('|', market_segment, distribution_channel, agent_code, company_code)) AS channel_key,
    market_segment,
    distribution_channel,
    agent_code,
    company_code
FROM distinct_channels
