-- ============================================================================
-- SEED LỊCH SỬ ETL CHO DASHBOARD GIÁM SÁT (Seminar 3 - Hạng mục 3.1)
-- Nạp 14 dòng vào control.etl_batch_log: 10 lần chạy ingestion + 4 lần dbt build, trải trên 7 ngày gần nhất.
--
-- Kịch bản (dựa trên các lần chạy thật ở Seminar 1; lỗi kết nối và các lần chạy lại được mô phỏng):
--   FULL                 : batch_01 lỗi kết nối (FAILED) -> chạy lại thành công (RETRY_SUCCESS)
--   INCREMENTAL SUCCESS  : batch_03
--   INCREMENTAL WARNING  : batch_02 (1 dòng adr < 0 bị loại) và batch_04 (13/40 dòng lỗi giá trị)
--   INCREMENTAL FAILED   : batch_05 sai cấu trúc (thiếu cột adr) -> sửa file -> RETRY_SUCCESS
--   INCREMENTAL SUCCESS  : chạy lại batch_03 (upsert, không nhân đôi) và 2 lần chạy theo lịch không có batch mới
--   hotel_dbt_build      : 4 dòng, rows_extracted = tổng test, rows_valid = test PASS, rows_rejected = test FAIL
--
-- Cách dùng (chạy MỘT lần trên bảng còn trống, trước khi chạy pipeline thật):
--   docker exec -i lab-postgres psql -U postgres -d dw_lab < postgres/seed/seed_etl_history.sql
-- Script tự bỏ qua nếu bảng đã có dữ liệu. Muốn nạp lại: TRUNCATE control.etl_batch_log RESTART IDENTITY;
-- ============================================================================

DO $seed$
DECLARE
    d0 TIMESTAMP := date_trunc('day', NOW()) - INTERVAL '7 days';   -- ngày bắt đầu lịch sử (dòng cuối rơi vào hôm qua, không bao giờ ở tương lai)
BEGIN
    IF EXISTS (SELECT 1 FROM control.etl_batch_log) THEN
        RAISE NOTICE 'control.etl_batch_log đã có dữ liệu, bỏ qua seed. Chạy TRUNCATE ... RESTART IDENTITY trước nếu muốn nạp lại.';
        RETURN;
    END IF;

    INSERT INTO control.etl_batch_log
        (pipeline_name, batch_file, load_mode, rows_extracted, rows_valid, rows_rejected,
         status, error_message, started_at, completed_at, duration_seconds)
    SELECT v.pipeline_name, v.batch_file, v.load_mode, v.rows_extracted, v.rows_valid, v.rows_rejected,
           v.status, v.error_message,
           d0 + v.start_offset,
           d0 + v.start_offset + make_interval(secs => v.duration_seconds::double precision),
           v.duration_seconds
    FROM (VALUES
        -- Ngày 1: Full Load lần đầu bị lỗi kết nối, chạy lại thành công, rồi dbt build
        ('hotel_ingestion_pipeline', 'batch_01_full_2015_2016.csv', 'FULL', 0, 0, 0, 'FAILED',
         'psycopg2.OperationalError: could not translate host name "postgres" to address: Name or service not known',
         INTERVAL '9 hours 12 minutes', 3.40),
        ('hotel_ingestion_pipeline', 'batch_01_full_2015_2016.csv', 'FULL', 78703, 78703, 0, 'RETRY_SUCCESS',
         'Chạy lại thành công sau lần FAILED trước đó.',
         INTERVAL '9 hours 30 minutes', 71.00),
        ('hotel_dbt_build', 'batch_01_full_2015_2016.csv', 'DBT', 43, 43, 0, 'SUCCESS',
         'dbt run: 7/7 model OK | dbt test: 43/43 PASS',
         INTERVAL '9 hours 32 minutes', 103.00),

        -- Ngày 2: Incremental đợt 1 (có 1 dòng adr âm bị loại)
        ('hotel_ingestion_pipeline', 'batch_02_inc_2017_H1.csv', 'INCREMENTAL', 30449, 30448, 1, 'WARNING',
         'Đã loại 1 dòng lỗi giá trị.',
         INTERVAL '1 day 2 hours', 87.00),
        ('hotel_dbt_build', 'batch_02_inc_2017_H1.csv', 'DBT', 43, 43, 0, 'SUCCESS',
         'dbt run: 7/7 model OK | dbt test: 43/43 PASS',
         INTERVAL '1 day 2 hours 3 minutes', 101.00),

        -- Ngày 3: Incremental đợt 2 (10.238 dòng mới + 300 dòng cập nhật)
        ('hotel_ingestion_pipeline', 'batch_03_inc_2017_H2.csv', 'INCREMENTAL', 10538, 10538, 0, 'SUCCESS',
         NULL,
         INTERVAL '2 days 2 hours', 59.00),
        ('hotel_dbt_build', 'batch_03_inc_2017_H2.csv', 'DBT', 43, 43, 0, 'SUCCESS',
         'dbt run: 7/7 model OK | dbt test: 43/43 PASS',
         INTERVAL '2 days 2 hours 2 minutes', 104.00),

        -- Ngày 4: chạy lại cùng batch để kiểm tra upsert (tổng dòng stage không đổi)
        ('hotel_ingestion_pipeline', 'batch_03_inc_2017_H2.csv', 'INCREMENTAL', 10538, 10538, 0, 'SUCCESS',
         NULL,
         INTERVAL '3 days 10 hours 15 minutes', 70.00),

        -- Ngày 5: file có dòng lỗi giá trị => WARNING; file sai cấu trúc => FAILED, sửa file rồi chạy lại
        ('hotel_ingestion_pipeline', 'batch_04_corrupted_test.csv', 'INCREMENTAL', 40, 27, 13, 'WARNING',
         'Đã loại 13 dòng lỗi giá trị.',
         INTERVAL '4 days 14 hours 20 minutes', 30.00),
        ('hotel_ingestion_pipeline', 'batch_05_bad_schema.csv', 'INCREMENTAL', 20, 0, 20, 'FAILED',
         '[validate_hotel_data] batch_05_bad_schema.csv: thiếu cột bắt buộc [''adr'']. File có 31 cột dữ liệu, yêu cầu 32 cột.',
         INTERVAL '4 days 14 hours 35 minutes', 4.10),
        ('hotel_ingestion_pipeline', 'batch_05_bad_schema.csv', 'INCREMENTAL', 20, 20, 0, 'RETRY_SUCCESS',
         'Chạy lại thành công sau lần FAILED trước đó.',
         INTERVAL '4 days 15 hours 10 minutes', 18.00),
        ('hotel_dbt_build', 'batch_05_bad_schema.csv', 'DBT', 43, 43, 0, 'SUCCESS',
         'dbt run: 7/7 model OK | dbt test: 43/43 PASS',
         INTERVAL '4 days 15 hours 11 minutes', 99.00),

        -- Ngày 6, 7: trigger lập lịch 02:00 chạy nhưng không còn batch mới
        ('hotel_ingestion_pipeline', 'AUTO: không có batch mới', 'INCREMENTAL', 0, 0, 0, 'SUCCESS',
         'Không có batch mới trong data/ cần nạp.',
         INTERVAL '5 days 2 hours', 0.60),
        ('hotel_ingestion_pipeline', 'AUTO: không có batch mới', 'INCREMENTAL', 0, 0, 0, 'SUCCESS',
         'Không có batch mới trong data/ cần nạp.',
         INTERVAL '6 days 2 hours', 0.55)
    ) AS v(pipeline_name, batch_file, load_mode, rows_extracted, rows_valid, rows_rejected,
           status, error_message, start_offset, duration_seconds)
    ORDER BY v.start_offset;

    RAISE NOTICE 'Đã nạp % dòng lịch sử vào control.etl_batch_log.', (SELECT COUNT(*) FROM control.etl_batch_log);
END
$seed$;

-- Kiểm tra nhanh
SELECT run_id, pipeline_name, batch_file, load_mode, rows_extracted, rows_valid, rows_rejected, status,
       TO_CHAR(started_at, 'YYYY-MM-DD HH24:MI') AS started_at, duration_seconds
FROM control.etl_batch_log
ORDER BY run_id;
