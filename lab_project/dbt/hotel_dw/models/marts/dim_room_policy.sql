-- Phụ trách chính (Giai đoạn 1): Phạm Ngọc Thanh
WITH distinct_policies AS (
    SELECT DISTINCT reserved_room_type, assigned_room_type, meal_code, deposit_type FROM {{ ref('stg_hotel_bookings') }}
)
SELECT
    MD5(CONCAT_WS('|', reserved_room_type, assigned_room_type, meal_code, deposit_type)) AS policy_key,
    reserved_room_type,
    assigned_room_type,
    CASE WHEN reserved_room_type <> assigned_room_type THEN TRUE ELSE FALSE END AS is_room_changed,
    meal_code,
    CASE meal_code
        WHEN 'BB' THEN 'Bed & Breakfast'
        WHEN 'HB' THEN 'Half Board (Breakfast + Dinner)'
        WHEN 'FB' THEN 'Full Board (All Meals)'
        WHEN 'SC' THEN 'Self Catering (No Meals)'
        ELSE 'Undefined / No Meal Package'
    END AS meal_description,
    deposit_type
FROM distinct_policies
