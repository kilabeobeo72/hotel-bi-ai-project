-- Phụ trách chính (Giai đoạn 1): Phạm Ngọc Thanh
-- Bảng chiều Thời gian (Dim Date) phục vụ phân tích theo Năm, Quý, Tháng, Tuần, Cuối tuần

WITH date_series AS (
    SELECT generate_series(
        DATE '2014-01-01',
        DATE '2018-12-31',
        INTERVAL '1 day'
    )::DATE AS full_date
)

SELECT
    CAST(TO_CHAR(full_date, 'YYYYMMDD') AS INTEGER) AS date_key,
    full_date,
    EXTRACT(YEAR FROM full_date)::INTEGER AS year,
    EXTRACT(QUARTER FROM full_date)::INTEGER AS quarter,
    'Q' || EXTRACT(QUARTER FROM full_date)::TEXT AS quarter_name,
    EXTRACT(MONTH FROM full_date)::INTEGER AS month,
    TO_CHAR(full_date, 'FMMonth') AS month_name,
    EXTRACT(WEEK FROM full_date)::INTEGER AS week_of_year,
    EXTRACT(DAY FROM full_date)::INTEGER AS day_of_month,
    EXTRACT(ISODOW FROM full_date)::INTEGER AS day_of_week,
    TO_CHAR(full_date, 'FMDay') AS day_name,
    CASE WHEN EXTRACT(ISODOW FROM full_date) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM date_series
