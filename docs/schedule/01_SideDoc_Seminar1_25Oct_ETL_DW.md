# 📘 SIDE DOC 1: KẾ HOẠCH GIAI ĐOẠN 1 – SEMINAR 1 (25/10 – 27/10/2026)

> **Chủ đề Seminar 1 (Tuần 7):** *Modeling & Nạp dữ liệu từ [Source] vào Kho dữ liệu (Data Ingestion + dbt Transformation + Star Schema DW)*
> **Hạn chót nội bộ nhóm:** **23:59 Ngày 25/10/2026** (Chuẩn bị sẵn sàng cho buổi gọi ngẫu nhiên ngày **27/10/2026**)
> **Phạm vi yêu cầu đề bài giải quyết trong Giai đoạn 1:** Mục **2**, **3.1** (Mage.ai Ingestion), **3.2** (dbt Transformation & Tests), **3.3** (Data Warehouse Star Schema).

---

## 1. MỤC TIÊU CỐT LÕI CỦA GIAI ĐOẠN 1 

1. **Bài toán & Thiết kế Dimensional Model (Star Schema):** Giải thích được tại sao chọn bộ dữ liệu *Hotel Booking Demand (32 cột)*, xác định đúng **Grain** của bảng Fact, và chiếu sơ đồ **Star Schema** gồm `dds.fact_bookings` nối với 5 bảng `dds.dim_*`.
2. **Data Ingestion bằng Mage.ai vào vùng `stage`:**
   - Chạy thử nạp **Full Load** (`batch_01_full_2015_2016.csv` ~ 79.000 dòng) và **Incremental Load** (`batch_02_inc_2017_H1.csv`, `batch_03_inc_2017_H2.csv` ~ 40.000 dòng).
   - Có block kiểm tra chất lượng dữ liệu cơ bản (`validate_hotel_data.py`).
   - Ghi nhận trạng thái thực thi, số lượng bản ghi xử lý và lỗi phát sinh vào bảng `control.etl_batch_log`.
3. **Data Transformation bằng dbt từ `stage` sang `dds`:**
   - Chạy lệnh `dbt run` tạo ra bảng làm sạch `stg_hotel_bookings` và 6 bảng kho dữ liệu (`dim_date`, `dim_hotel`, `dim_customer`, `dim_channel`, `dim_room_policy`, `fact_bookings`).
   - Chạy lệnh `dbt test` pass 100% các ràng buộc khóa chính (`unique`, `not_null`), khóa ngoại (`relationships`) và miền giá trị (`accepted_values`).
   - Mở giao diện `dbt docs` chiếu sơ đồ **Lineage Graph (DAG)** thể hiện quan hệ phụ thuộc rõ ràng từ `source` $\rightarrow$ `staging` $\rightarrow$ `marts (dds)`.

---

## 2. PHÂN CÔNG THEO HẠNG MỤC CÔNG VIỆC 


### HẠNG MỤC 1.1: Thiết lập Hạ tầng Docker, Schema Database & dbt Staging
- **Người phụ trách chính:** **Đào Trung Kiên** *(Nhóm trưởng)*
- **Thời gian hoàn thành:** Ngày 19/10 – 22/10/2026
- **Nhiệm vụ Kỹ thuật (Code):**
  1. Khởi tạo và kiểm tra `compose.yaml` + `Dockerfile` chạy ổn định PostgreSQL 17 (`port 5432`) và Mage.ai (`port 6789`) kèm thư viện `dbt-postgres`.
  2. Hoàn thiện file `postgres/init/01_init.sql` tự động tạo 3 schema: `stage`, `dds`, `control` và bảng `stage.raw_hotel_bookings` (để Thanh và Ý có thể test SQL ngay lập tức mà không cần đợi Dương chạy xong Mage).
  3. Khởi tạo project dbt tại `lab_project/dbt/hotel_dw/` (`dbt_project.yml`, `profiles.yml`, `sources.yml`).
  4. Viết model làm sạch `models/staging/stg_hotel_bookings.sql`:
     - Sinh khóa định danh `booking_id` (MD5/hash hoặc row_number kết hợp các thuộc tính giao dịch).
     - Xử lý giá trị `NULL` hoặc chuỗi `'NULL'` trong CSV gốc (cột `children` $\rightarrow$ `0`, `country` $\rightarrow$ `'UNK'`, `agent` $\rightarrow$ `'No Agent'`, `company` $\rightarrow$ `'No Company'`).
     - Ghép 3 cột `arrival_date_year`, `arrival_date_month`, `arrival_date_day_of_month` thành cột kiểu `DATE` chuẩn `arrival_date`.
     - Loại bỏ các bản ghi vô lý (ví dụ: `adults + children + babies = 0` hoặc `adr < 0`).
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Chương 1 (Kiến trúc Hệ thống tổng thể)** và **Chương 3 – Mục 3.2.1 (Chuẩn hóa & Làm sạch dữ liệu tầng Staging)** trong file Báo cáo.

---

### HẠNG MỤC 1.2: Cắt Batch Dữ Liệu & Xây Dựng Pipeline Data Ingestion trên Mage.ai
- **Người phụ trách chính:** **Huỳnh Võ Đại Dương**
- **Thời gian hoàn thành:** Ngày 20/10 – 23/10/2026
- **Nhiệm vụ Kỹ thuật (Code):**
  1. Tải file `hotel_bookings.csv` từ Kaggle bỏ vào thư mục `data/`, chạy và tinh chỉnh script `data/split_batches.py` để tách thành 4 file giả lập thực tế:
     - `batch_01_full_2015_2016.csv`: Dữ liệu lịch sử năm 2015 & 2016 (Dùng cho **Full Load**).
     - `batch_02_inc_2017_Q1_Q2.csv`: Dữ liệu nửa đầu năm 2017 (Dùng cho **Incremental Load** lần 1).
     - `batch_03_inc_2017_Q3.csv`: Dữ liệu quý 3 năm 2017 (Dùng cho **Incremental Load** lần 2 + test cập nhật bản ghi trùng).
     - `batch_04_corrupted_test.csv`: File có vài dòng lỗi (ví dụ thiếu cột bắt buộc hoặc `adr` âm) để demo khả năng bắt lỗi của pipeline.
  2. Xây dựng Pipeline `hotel_ingestion_pipeline` trên Mage.ai gồm các block:
     - **Data Loader (`load_hotel_csv.py`):** Đọc file CSV từ biến runtime `batch_file` và `load_mode` (`full` hoặc `incremental`), gắn thêm cột metadata `batch_file`, `ingested_at`, `record_hash`.
     - **Transformer (`validate_hotel_data.py`):** Kiểm tra danh sách 32 cột bắt buộc, ép kiểu số (`lead_time`, `adr`, `is_canceled`), lọc/báo lỗi nếu vi phạm quy tắc cơ bản.
     - **Data Exporter (`load_stage_hotel.py`):** Nạp vào bảng `stage.raw_hotel_bookings`. Nếu `load_mode == 'full'` thì `replace`/`truncate`, nếu `load_mode == 'incremental'` thì `append` có kiểm tra chống trùng theo `record_hash` (`unique_conflict_method='UPDATE'`).
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Chương 3 – Mục 3.1 (Thiết kế Pipeline Data Ingestion với Mage.ai: Full Load, Incremental Load & Validation)** kèm ảnh chụp màn hình cây Pipeline trên Mage.ai.

---

### HẠNG MỤC 1.3: Thiết kế Star Schema & Xây dựng các mô hình Fact/Dimension bằng dbt
- **Người phụ trách chính:** **Phạm Ngọc Thanh**
- **Thời gian hoàn thành:** Ngày 20/10 – 23/10/2026
- **Nhiệm vụ Kỹ thuật (Code):**
  1. Vẽ sơ đồ **Star Schema (ERD)** của tầng `dds` (sử dụng `dbdiagram.io` hoặc `draw.io`).
  2. Viết 6 file SQL trong thư mục `lab_project/dbt/hotel_dw/models/marts/` để đẩy dữ liệu vào schema `dds`:
     - `dim_date.sql`: Tạo bảng chiều thời gian đầy đủ từ năm 2014 đến 2018 (`date_key`, `full_date`, `year`, `quarter`, `month`, `month_name`, `week_of_year`, `day_of_week`, `is_weekend`).
     - `dim_hotel.sql`: `hotel_key`, `hotel_name`, `hotel_category`.
     - `dim_customer.sql`: `customer_key`, `country_code`, `customer_type`, `is_repeated_guest`, `guest_group_type` (Solo, Couple, Family, Group).
     - `dim_channel.sql`: `channel_key`, `market_segment`, `distribution_channel`, `agent_code`, `company_code`.
     - `dim_room_policy.sql`: `policy_key`, `reserved_room_type`, `assigned_room_type`, `is_room_upgraded` (`reserved != assigned`), `meal_code`, `meal_description`, `deposit_type`.
     - `fact_bookings.sql`: Kết nối (JOIN) `stg_hotel_bookings` với 5 bảng `dim_*` qua các Surrogate Key (`hotel_key`, `customer_key`, `channel_key`, `policy_key`, `arrival_date_key`, `status_date_key`) và tính sẵn các Measures: `total_nights`, `total_guests`, `adr`, `gross_revenue` (`adr * total_nights`), `actual_revenue` (khi `is_canceled = 0`), `revenue_loss` (khi `is_canceled = 1`), `lead_time`, `is_canceled`, `booking_changes`, `total_of_special_requests`.
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Chương 2 (Mô tả Dataset Kaggle, Bối cảnh nghiệp vụ Khách sạn, Danh sách câu hỏi phân tích)** và **Chương 3 – Mục 3.3 (Thiết kế Kho dữ liệu đa chiều Star Schema: Quy trình nghiệp vụ, Grain, Bảng Fact & Dimension)**.

---

### HẠNG MỤC 1.4: Cơ chế Ghi Log Thực Thi (`control`) & Kiểm định Chất lượng (`dbt test` + `dbt docs`)
- **Người phụ trách chính:** **Thạch Ý**
- **Thời gian hoàn thành:** Ngày 20/10 – 24/10/2026
- **Nhiệm vụ Kỹ thuật (Code):**
  1. Thiết kế bảng `control.etl_batch_log` trong PostgreSQL và viết block/hàm Python `log_etl_execution.py` trên Mage.ai để mỗi lần chạy pipeline (dù `SUCCESS` hay `FAILED`), hệ thống đều ghi lại:
     - `run_id`, `pipeline_name`, `batch_file`, `load_mode` (`FULL` / `INCREMENTAL`), `rows_extracted`, `rows_valid`, `rows_rejected`, `status` (`SUCCESS` / `FAILED`), `error_message`, `started_at`, `completed_at`, `duration_seconds`.
  2. Viết file `models/marts/schema.yml` và `models/staging/stg_schema.yml` trong `dbt`:
     - Thiết lập `dbt test` cho tất cả các bảng: `unique` & `not_null` cho mọi khóa chính (`booking_id`, `hotel_key`, `customer_key`, `channel_key`, `policy_key`, `date_key`).
     - Thiết lập `relationships` kiểm tra toàn vẹn khóa ngoại từ `fact_bookings` sang 5 bảng `dim_*`.
     - Thiết lập `accepted_values` cho `is_canceled` (`[0, 1]`), `hotel_name` (`['Resort Hotel', 'City Hotel']`), `deposit_type` (`['No Deposit', 'Non Refund', 'Refundable']`).
     - Viết mô tả (`description`) tiếng Việt/Anh rõ ràng cho từng bảng và từng cột trong `schema.yml` để chạy `dbt docs generate` ra trang tài liệu Data Catalog hoàn chỉnh.
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Chương 3 – Mục 3.1.4 (Cơ chế Audit Log & Xử lý lỗi trong schema `control`)**, **Mục 3.2.2 (Kiểm tra chất lượng dữ liệu với dbt tests & Tài liệu hóa dbt docs)**, và ghép toàn bộ bài viết của 4 thành viên thành bản **Báo cáo Giai đoạn 1 + Slide thuyết trình Seminar 1**.

