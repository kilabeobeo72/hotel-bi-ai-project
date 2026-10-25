-- ============================================================================
-- KHỞI TẠO CẤU TRÚC KHO DỮ LIỆU KHÁCH SẠN
-- 3 Schemas chuẩn:
--   1. stage   : Chứa dữ liệu thô nạp từ Mage.ai (Full & Incremental Load)
--   2. dds     : Dimensional Data Store (Star Schema do dbt xây dựng)
--   3. control : Ghi nhận trạng thái thực thi ETL, số dòng xử lý và lỗi phát sinh
CREATE SCHEMA IF NOT EXISTS stage;
CREATE SCHEMA IF NOT EXISTS dds;
CREATE SCHEMA IF NOT EXISTS control;

CREATE TABLE IF NOT EXISTS control.etl_batch_log (
    run_id              SERIAL PRIMARY KEY,
    pipeline_name       VARCHAR(100) NOT NULL,
    batch_file          VARCHAR(150) NOT NULL,
    load_mode           VARCHAR(30)  NOT NULL, -- 'FULL' hoặc 'INCREMENTAL'
    rows_extracted      INTEGER      DEFAULT 0,
    rows_valid          INTEGER      DEFAULT 0,
    rows_rejected       INTEGER      DEFAULT 0,
    status              VARCHAR(30)  NOT NULL, -- 'SUCCESS', 'FAILED', 'WARNING'
    error_message       TEXT,
    started_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP,
    duration_seconds    NUMERIC(10, 2)
);
